"""Shared stock ledger. Qt-free; amounts are toman, quantities are base units."""
import copy, math, uuid
from datetime import date, datetime

def uid():return str(uuid.uuid4())
def stamp():return datetime.now().isoformat()
def mother(data,p):return next((m for m in data.get('mothers',[]) if m['id']==p.get('motherId')),None)
def variants(m):return {v['id']:v for v in m['variants']}
def label(v):return ' / '.join(x for x in [v.get('color',''),v.get('size','')] if x) or 'بدون تنوع'
def fees(data,p):return {**data['digiFees'],**p.get('digiFeeOverride',{})}
def effective_rate(data,p):
 c=p.get('purchasePrice',0)
 return (p['targetPriceOverride']/c-1)*100 if 'targetPriceOverride' in p and c else p.get('profitRateOverride',data['profitRate'])
def target(data,p):return p.get('targetPriceOverride',math.floor(p['purchasePrice']*(1+effective_rate(data,p)/100)+.5))
def channel_target(data,p,channel):
 override=p.get('platformProfitOverrides',{}).get(channel,{})
 if 'amount' in override:return override['amount']
 if 'rate' in override:return math.floor(p['purchasePrice']*(1+override['rate']/100)+.5)
 return target(data,p)
def channel_rate(data,p,channel):
 override=p.get('platformProfitOverrides',{}).get(channel,{})
 if 'rate' in override:return override['rate']
 if 'amount' in override:return (override['amount']/p['purchasePrice']-1)*100 if p['purchasePrice'] else 0
 return effective_rate(data,p)
def replay(data,m,before=None):
 state={v['id']:[0,float(v.get('openingUnitCost',0))] for v in m['variants']}
 records=[e for e in data.get('purchases',[])+data.get('sales',[])+data.get('inventoryAdjustments',[]) if e.get('motherId')==m['id'] and not e.get('cancelled')]
 records.sort(key=lambda e:(e['date'],e.get('createdAt',''),e['id']))
 for e in records:
  if before and (e['date'],e.get('createdAt',''),e['id'])>=(before['date'],before.get('createdAt',''),before['id']):break
  kind=e.get('kind','sale')
  for line in e.get('lines',[]):
   key=line['variantId'];q=line['quantity']
   if key not in state:raise ValueError('تنوع ثبت‌شده در سابقه دیگر وجود ندارد.')
   old,cost=state[key]
   if kind=='purchase':
    new=old+q;cost=(old*cost+q*line['unitCost'])/new if new else 0
   elif kind=='adjust':new=old+q
   else:new=old-q
   if new<0:raise ValueError('این تغییر باعث موجودی منفی در تاریخ '+e['date']+' می‌شود.')
   state[key]=[new,cost]
 return state

def sync(data):
 for m in data.get('mothers',[]):
  state=replay(data,m)
  for v in m['variants']:v['stock'],v['averageCost']=state[v['id']]
  count=sum(v['stock'] for v in m['variants']);cost=sum(v['stock']*v['averageCost'] for v in m['variants'])/count if count else m.get('lastUnitCost',0)
  if count:m['lastUnitCost']=cost
  for p in data.get('active',[])+data.get('deleted',[]):
   if p.get('motherId')==m['id']:p['stock']=count//p['packSize'];p['purchasePrice']=math.floor(cost*p['packSize']+.5)

def transact(data,collection,record,existing=None):
 trial=copy.deepcopy(data);items=trial.setdefault(collection,[])
 if existing:
  old=next(e for e in items if e['id']==existing['id']);old.clear();old.update(copy.deepcopy(record))
 else:items.append(copy.deepcopy(record))
 sync(trial)
 if existing:existing.clear();existing.update(record)
 else:data.setdefault(collection,[]).append(record)
 sync(data)

def add_purchase(data,m,lines,day,supplier_id=None,existing=None):
 date.fromisoformat(day)
 if day>date.today().isoformat():raise ValueError('تاریخ آینده مجاز نیست.')
 if not lines or any(l['quantity']<=0 or l['unitCost']<0 for l in lines):raise ValueError('تعداد و قیمت خرید معتبر نیست.')
 e=dict(id=existing['id'] if existing else uid(),motherId=m['id'],kind='purchase',date=day,createdAt=existing.get('createdAt',stamp()) if existing else stamp(),supplierId=supplier_id,lines=copy.deepcopy(lines))
 transact(data,'purchases',e,existing);return e

def cancel_record(data,collection,e):
 replacement={**e,'cancelled':True};transact(data,collection,replacement,e)

def add_sale(data,p,quantity,allocations,channel,unit_price,fee_snapshot,existing=None):
 m=mother(data,p)
 if not m:raise ValueError('کالای مادر پیدا نشد.')
 if quantity<=0 or sum(l['quantity'] for l in allocations)!=quantity*p['packSize']:raise ValueError('مجموع رنگ و سایز باید برابر تعداد فروش × تعداد داخل پک باشد.')
 if any(l['quantity']<=0 for l in allocations) or len({l['variantId'] for l in allocations})!=len(allocations):raise ValueError('انتخاب تنوع معتبر نیست.')
 available=replay(data,m)
 if existing:
  for l in existing['lines']:available[l['variantId']][0]+=l['quantity']
 for l in allocations:
  if l['variantId'] not in available or l['quantity']>available[l['variantId']][0]:raise ValueError('موجودی رنگ یا سایز انتخاب‌شده کافی نیست.')
 costs=replay(data,m,before=existing) if existing else available
 old_costs={l['variantId']:l.get('unitCostAtSale',costs[l['variantId']][1]) for l in existing['lines']} if existing else {}
 allocations=copy.deepcopy(allocations)
 for l in allocations:l['unitCostAtSale']=old_costs.get(l['variantId'],costs[l['variantId']][1])
 cost=sum(l['unitCostAtSale']*l['quantity'] for l in allocations)/quantity
 e=dict(id=existing['id'] if existing else uid(),motherId=m['id'],productId=p['id'],productName=p['name'],kind='sale',date=existing['date'] if existing else date.today().isoformat(),createdAt=existing.get('createdAt',stamp()) if existing else stamp(),quantity=quantity,packSize=p['packSize'],channel=channel,unitPrice=unit_price,totalPrice=quantity*unit_price,purchasePriceAtSale=cost,feeSnapshot=copy.deepcopy(fee_snapshot),lines=copy.deepcopy(allocations))
 transact(data,'sales',e,existing);return e

def adjust(data,m,quantities):
 state=replay(data,m);lines=[dict(variantId=k,quantity=q-state[k][0]) for k,q in quantities.items() if q!=state[k][0]]
 if lines:transact(data,'inventoryAdjustments',dict(id=uid(),motherId=m['id'],kind='adjust',date=date.today().isoformat(),createdAt=stamp(),lines=lines))

def initialize(data,root):
 if data.get('inventorySchema')==2 and data.get('businessReset27'):return
 # Explicitly requested V2.7 one-time reset; keep the supplier directory.
 import json
 folder=root/'backups';folder.mkdir(parents=True,exist_ok=True)
 (folder/('before-reset-v2.7-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 for k in ['active','deleted','sales','history','stockEvents','generalPurchases','mothers','purchases','inventoryAdjustments']:data[k]=[]
 data.setdefault('suppliers',[]);data.update(inventorySchema=2,businessReset27=True,arazmanDeductionRate=6.6)
