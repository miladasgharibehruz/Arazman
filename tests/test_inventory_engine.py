import copy, tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pathlib import Path
import inventory_engine as E
from datetime import date
D=date.today().isoformat()
class InventoryTests(unittest.TestCase):
 def setUp(self):
  self.d=dict(inventorySchema=2,active=[],deleted=[],mothers=[],purchases=[],sales=[],inventoryAdjustments=[],profitRate=25,digiFees=dict(processing_percent=7,processing_min=36000,processing_max=240000,label_cost=6000,tax_percent=10))
  self.m=dict(id='m',name='اسکاچ',variants=[dict(id='blue',color='آبی'),dict(id='red',color='قرمز'),dict(id='green',color='سبز')]);self.d['mothers']=[self.m]
  self.p=dict(id='p',motherId='m',packSize=1,purchasePrice=100,stock=0,name='تکی');self.pack=dict(id='p3',motherId='m',packSize=3,purchasePrice=300,stock=0,name='سه تایی');self.d['active']=[self.p,self.pack]
  self.buy=E.add_purchase(self.d,self.m,[dict(variantId=v['id'],quantity=10,unitCost=100) for v in self.m['variants']],D)
 def sell(self,p,q,lines,existing=None):return E.add_sale(self.d,p,q,[dict(variantId=k,quantity=v) for k,v in lines], 'inperson',500,{},existing)
 def test_shared_and_mixed(self):
  s=self.sell(self.pack,1,[('blue',3)]);self.assertEqual((self.p['stock'],self.pack['stock']),(27,9));self.assertEqual(self.m['variants'][0]['stock'],7)
  self.sell(self.pack,1,[('blue',1),('red',1),('green',1)]);self.assertEqual(self.p['stock'],24)
  E.cancel_record(self.d,'sales',s);self.assertEqual(self.p['stock'],27);self.assertEqual(self.m['variants'][0]['stock'],9)
 def test_reject_oversell_atomic(self):
  before=copy.deepcopy(self.d)
  with self.assertRaises(ValueError):self.sell(self.pack,4,[('blue',12)])
  self.assertEqual(before,self.d)
 def test_edit_allocation(self):
  s=self.sell(self.pack,1,[('blue',3)]);self.sell(self.pack,2,[('red',6)],s);self.assertEqual(self.p['stock'],24);self.assertEqual(self.m['variants'][0]['stock'],10);self.assertEqual(self.m['variants'][1]['stock'],4)
 def test_weighted_buy_and_history(self):
  s=self.sell(self.p,2,[('blue',2)]);E.add_purchase(self.d,self.m,[dict(variantId='blue',quantity=8,unitCost=200)],D)
  self.assertEqual(self.m['variants'][0]['averageCost'],150);self.assertEqual(s['purchasePriceAtSale'],100);self.assertEqual(self.pack['purchasePrice'],367)
 def test_purchase_cancel_negative(self):
  self.sell(self.p,1,[('blue',1)]);before=copy.deepcopy(self.d)
  with self.assertRaises(ValueError):E.cancel_record(self.d,'purchases',self.buy)
  self.assertEqual(self.d,before)
 def test_adjust_is_not_purchase(self):
  E.adjust(self.d,self.m,{'blue':7,'red':8,'green':9});self.assertEqual(self.p['stock'],24);self.assertEqual(len(self.d['purchases']),1)
 def test_exact_price_and_overrides(self):
  self.p['targetPriceOverride']=4300000;self.assertEqual(E.target(self.d,self.p),4300000);self.p['digiFeeOverride']={'processing_min':22500};self.assertEqual(E.fees(self.d,self.p)['processing_min'],22500);self.assertEqual(self.d['digiFees']['processing_min'],36000)
 def test_reset_once_and_backup(self):
  with tempfile.TemporaryDirectory() as temp:
   data={'active':[{'name':'old'}], 'profitRate':30,'theme':'تیره و نئونی'};E.initialize(data,Path(temp));self.assertEqual(len(list((Path(temp)/'backups').glob('*.json'))),1);self.assertEqual(data['active'],[]);data['active']=[{'name':'new'}];E.initialize(data,Path(temp));self.assertEqual(data['active'][0]['name'],'new');self.assertEqual(data['profitRate'],30)
 def test_empty_stock_retains_entered_cost(self):
  data=copy.deepcopy(self.d);data['purchases']=[];data['mothers'][0]['lastUnitCost']=100
  for v in data['mothers'][0]['variants']:v['openingUnitCost']=100
  E.sync(data);self.assertEqual(data['active'][0]['stock'],0);self.assertEqual(data['active'][0]['purchasePrice'],100)
 def test_historic_sale_edit_keeps_original_cost(self):
  s=self.sell(self.p,1,[('blue',1)]);E.add_purchase(self.d,self.m,[dict(variantId='blue',quantity=9,unitCost=300)],D)
  self.sell(self.p,2,[('blue',2)],s);self.assertEqual(s['purchasePriceAtSale'],100)
if __name__=='__main__':unittest.main()

