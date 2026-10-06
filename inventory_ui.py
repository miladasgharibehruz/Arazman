"""Native inventory, purchasing, settlement and price detail dialogs."""
import copy, math
from datetime import date
import inventory_engine as E
from PySide6.QtCore import Qt, QTimer, QEvent, QObject, QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,QPushButton,QTabWidget,QSpinBox,QDoubleSpinBox,QAbstractSpinBox,QTableWidget,QTableWidgetItem,QHeaderView,QComboBox,QCheckBox,QDialogButtonBox,QDialog,QMenu,QScrollArea,QApplication)

def spin(value=0,percent=False):
 w=QDoubleSpinBox() if percent else QSpinBox();w.setRange(-100 if percent else 0,10000 if percent else 2000000000);w.setButtonSymbols(QAbstractSpinBox.NoButtons);w.setGroupSeparatorShown(True);w.setValue(value);return w

def table(headers):
 t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers);t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);t.verticalHeader().hide();return t

def fill(t,rows):
 t.setRowCount(len(rows))
 for r,row in enumerate(rows):
  for c,v in enumerate(row):
   text=(f'{v:,}' if isinstance(v,int) else str(v));t.removeCellWidget(r,c);t.setItem(r,c,QTableWidgetItem(text.translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'))))
 make_copyable(t)

def day_picker(app,api,parent,initial):
 d,l=app.dialog('انتخاب تاریخ شمسی');d.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint);c=api['PersianCalendar'](d);c.setWindowFlags(Qt.Widget);c.value=initial
 import jdatetime
 c.anchor=jdatetime.date.fromgregorian(date=date.fromisoformat(initial)).replace(day=1)
 def choose(day):
  value=day.togregorian().isoformat()
  if value<=api['today']():c.value=value;d.accept()
 c.choose=choose;c.draw();l.addWidget(c);c.show();d.resize(600,380)
 return c.value if d.exec()==QDialog.Accepted else initial

def supplier_combo(app,selected=None):
 c=QComboBox();c.addItem('بدون مرجع',None)
 for s in app.data['suppliers']:c.addItem(s['name'],s['id'])
 c.setCurrentIndex(max(0,c.findData(selected)));return c

def variants_input(layout,rows=None):
 t=table(['رنگ (اختیاری)','سایز (اختیاری)','تعداد واحد پایه','قیمت خرید هر واحد (تومان)']);layout.addWidget(t)
 fill(t,rows or [['','',0,0]])
 b=QPushButton('افزودن رنگ / سایز');layout.addWidget(b)
 def add():
  r=t.rowCount();t.insertRow(r)
  for col,val in enumerate(['','',0,0]):t.setItem(r,col,QTableWidgetItem(str(val)))
 b.clicked.connect(add);return t

def read_variants(t,api):
 rows=[];seen=set()
 for r in range(t.rowCount()):
  vals=[t.item(r,c).text().strip() if t.item(r,c) else '' for c in range(4)]
  q=int(api['num'](vals[2] or 0));cost=int(api['num'](vals[3] or 0))
  if q<0 or cost<0:raise ValueError('تعداد و قیمت نباید منفی باشند.')
  key=tuple(vals[:2])
  if key in seen:raise ValueError('ترکیب رنگ و سایز تکراری است.')
  seen.add(key);rows.append(dict(id=E.uid(),color=vals[0],size=vals[1],quantity=q,unitCost=cost))
 return rows

def package(app,m,size,api,name=None):
 p=dict(id=E.uid(),motherId=m['id'],packSize=size,name=name or m['name']+(' — تکی' if size==1 else ' — پک '+api['fa'](size)+' تایی'),stock=0,purchasePrice=0,firstPurchaseDate=m['firstPurchaseDate'])
 app.data['active'].append(p);return p

def add_product(app,api):
 d,l=app.dialog('افزودن کالا');d.resize(880,850);tabs=QTabWidget();tabs.setObjectName('settingsTabs');l.addWidget(tabs)
 basic=QWidget();bl=QVBoxLayout(basic);f=QFormLayout();bl.addLayout(f);name=QLineEdit();qty=spin();cost=spin();commission=QLineEdit();credit=QLineEdit();basalam=QLineEdit();supplier=supplier_combo(app)
 for label,w in [('نام کالای مادر',name),('موجودی بدون تنوع',qty),('قیمت خرید هر واحد پایه (تومان)',cost),('کمیسیون دیجیکالا — اختیاری (%)',commission),('کمیسیون اعتباری اضافه — اختیاری (%)',credit),('کمیسیون باسلام — اختیاری (%)',basalam),('مرجع خرید',supplier)]:f.addRow(label,w)
 purchase={'day':api['today']()};date_button=QPushButton('تاریخ امروز');date_label=QLabel('تاریخ خرید: '+api['fa'](api['jd'](purchase['day'])));bl.addWidget(date_label);bl.addWidget(date_button)
 calendar=api['PersianCalendar'](d);calendar.setWindowFlags(Qt.Widget);bl.addWidget(calendar);calendar.show()
 def set_date(day):
  if day>api['today']():return
  purchase['day']=day;date_label.setText('تاریخ خرید: '+api['fa'](api['jd'](day)))
 calendar.choose=lambda day:set_date(day.togregorian().isoformat())
 def select_date():set_date(api['today']());calendar.anchor=__import__('jdatetime').date.today().replace(day=1);calendar.draw()
 date_button.clicked.connect(select_date);basic_scroll=QScrollArea();basic_scroll.setWidgetResizable(True);basic_scroll.setFrameShape(QScrollArea.NoFrame);basic_scroll.setWidget(basic);tabs.addTab(basic_scroll,'کالای مادر');d.resize(880,min(850,QApplication.primaryScreen().availableGeometry().height()-40))
 variation=QWidget();vl=QVBoxLayout(variation);enabled=QCheckBox('این کالا رنگ یا سایز متفاوت دارد');vl.addWidget(enabled);vt=variants_input(vl);packs=QLineEdit('1');packs.setPlaceholderText('مثلاً 1,2,3,4,5,6');vl.addWidget(QLabel('تعداد داخل هر مدل فروش؛ جداشده با ویرگول'));vl.addWidget(packs);tabs.addTab(variation,'افزودن تنوع')
 notice=QLabel();notice.setWordWrap(True);l.addWidget(notice);save=QPushButton('ثبت کالا و خرید اولیه');l.addWidget(save)
 def commit():
  try:
   if not name.text().strip():raise ValueError('نام کالا الزامی است.')
   sizes=sorted(set(int(api['num'](x.strip())) for x in packs.text().replace('،',',').split(',')))
   if not sizes or min(sizes)<1:raise ValueError('تعداد داخل پک باید حداقل یک باشد.')
   vs=read_variants(vt,api) if enabled.isChecked() else [dict(id=E.uid(),color='',size='',quantity=qty.value(),unitCost=cost.value())]
   rates={}
   for key,w in [('commission',commission),('platformRate',credit),('basalamCommission',basalam)]:
    if w.text().strip():
     value=float(api['num'](w.text()));
     if not math.isfinite(value) or not 0<=value<100:raise ValueError('درصد کمیسیون باید از صفر تا کمتر از ۱۰۰ باشد.')
     rates[key]=value
   if rates.get('commission',0)+rates.get('platformRate',0)>=100:raise ValueError('مجموع کمیسیون نقدی و اضافه اعتباری باید کمتر از ۱۰۰ باشد.')
   draft=copy.deepcopy(app.data);m=dict(id=E.uid(),name=name.text().strip(),firstPurchaseDate=purchase['day'],variants=[dict(id=v['id'],color=v['color'],size=v['size'],openingUnitCost=v['unitCost']) for v in vs],lastUnitCost=sum(v['quantity']*v['unitCost'] for v in vs)/sum(v['quantity'] for v in vs) if sum(v['quantity'] for v in vs) else sum(v['unitCost'] for v in vs)/len(vs));draft['mothers'].append(m)
   lines=[dict(variantId=v['id'],quantity=v['quantity'],unitCost=v['unitCost']) for v in vs if v['quantity']]
   if lines:E.add_purchase(draft,m,lines,purchase['day'],supplier.currentData())
   app.data=draft
   for size in sizes:
    p=package(app,m,size,api);p.update(rates)
    if supplier.currentData():p['supplierId']=supplier.currentData()
   E.sync(app.data)
   for p in app.data['active']:
    if p.get('motherId')==m['id']:app.baselines(p);p['initialPendingPrices']=['arazman']
   app.persist();app.render();d.accept()
  except (ValueError,TypeError) as ex:notice.setText(str(ex))
 save.clicked.connect(commit);d.exec()

def purchase_dialog(app,api,product=None,existing=None):
 d,l=app.dialog('تغییر خرید' if existing else 'ثبت خرید');d.resize(830,600);combo=QComboBox()
 for m in app.data['mothers']:combo.addItem(m['name'],m['id'])
 l.addWidget(combo);supplier=supplier_combo(app,existing.get('supplierId') if existing else product.get('supplierId') if product else None);l.addWidget(supplier)
 t=table(['رنگ / سایز','تعداد خرید','قیمت خرید هر واحد']);l.addWidget(t);state={'day':existing['date'] if existing else api['today']()};datebutton=QPushButton();l.addWidget(datebutton)
 def select_date():state['day']=day_picker(app,api,d,state['day']);datebutton.setText('تاریخ: '+api['fa'](api['jd'](state['day'])))
 datebutton.setText('تاریخ: '+api['fa'](api['jd'](state['day'])));datebutton.clicked.connect(select_date)
 notice=QLabel();notice.setWordWrap(True);l.addWidget(notice);button=QPushButton('ثبت خرید');l.addWidget(button)
 def selected():return next((m for m in app.data['mothers'] if m['id']==combo.currentData()),None)
 def refresh():
  m=selected();old={x['variantId']:x for x in existing['lines']} if existing else {};fill(t,[[E.label(v),old.get(v['id'],{}).get('quantity',0),old.get(v['id'],{}).get('unitCost',round(v.get('averageCost',0)))] for v in m['variants']] if m else [])
  for r in range(t.rowCount()):t.item(r,0).setFlags(t.item(r,0).flags()&~Qt.ItemIsEditable)
 combo.currentIndexChanged.connect(refresh)
 if product:combo.setCurrentIndex(max(0,combo.findData(product.get('motherId'))))
 if existing:combo.setCurrentIndex(max(0,combo.findData(existing['motherId'])));combo.setEnabled(False)
 refresh()
 def commit():
  try:
   m=selected()
   if not m:raise ValueError('ابتدا کالای مادر را اضافه کنید.')
   lines=[]
   for r,v in enumerate(m['variants']):
    q=int(api['num'](t.item(r,1).text()));c=int(api['num'](t.item(r,2).text()))
    if q<0 or c<0:raise ValueError('تعداد و قیمت منفی مجاز نیست.')
    if q:lines.append(dict(variantId=v['id'],quantity=q,unitCost=c))
   E.add_purchase(app.data,m,lines,state['day'],supplier.currentData(),existing);app.persist();app.render();d.accept()
  except (ValueError,TypeError) as ex:notice.setText(str(ex))
 button.clicked.connect(commit);d.exec()

def edit_product(app,api):
 d,l=app.dialog('ویرایش کالا');d.resize(1080,min(860,QApplication.primaryScreen().availableGeometry().height()-40));search,listing=app.product_picker(l);tabs=QTabWidget();tabs.setObjectName('settingsTabs');l.addWidget(tabs);selected={'p':None};notice=QLabel();notice.setWordWrap(True);l.addWidget(notice)
 def page(title):w=QWidget();lay=QVBoxLayout(w);tabs.addTab(w,title);return lay
 basic=page('مشخصات');form=QFormLayout();basic.addLayout(form);name=QLineEdit();supplier=supplier_combo(app);form.addRow('نام مدل فروش',name);form.addRow('مرجع',supplier)
 pricing=page('سود اختصاصی');pf=QFormLayout();pricing.addLayout(pf);rate=spin(25,True);amount=spin();use_default=QCheckBox('استفاده از سود پیش‌فرض');pf.addRow('درصد سود',rate);pf.addRow('قیمت فروش دلخواه (تومان)',amount);pf.addRow(use_default);price_mode={'value':'rate'}
 def change_rate(value):
  if selected['p']:
   amount.blockSignals(True);amount.setValue(round(selected['p']['purchasePrice']*(1+value/100)));amount.blockSignals(False);price_mode['value']='rate';use_default.setChecked(False)
 def change_amount(value):
  if selected['p']:
   cost=selected['p']['purchasePrice'];rate.blockSignals(True);rate.setValue((value/cost-1)*100 if cost else 0);rate.blockSignals(False);price_mode['value']='amount';use_default.setChecked(False)
 rate.valueChanged.connect(change_rate);amount.valueChanged.connect(change_amount)
 def reset_default(checked):
  if checked and selected['p']:
   rate.blockSignals(True);amount.blockSignals(True);rate.setValue(app.data['profitRate']);amount.setValue(round(selected['p']['purchasePrice']*(1+app.data['profitRate']/100)));rate.blockSignals(False);amount.blockSignals(False)
 use_default.toggled.connect(reset_default)
 commissions=page('کمیسیون');cf=QFormLayout();commissions.addLayout(cf);commission=spin(0,True);credit=spin(0,True);basalam=spin(0,True)
 digi_enabled=QCheckBox('قیمت دیجیکالا فعال باشد');basalam_enabled=QCheckBox('قیمت باسلام فعال باشد');cf.addRow(digi_enabled);cf.addRow(basalam_enabled)
 for caption,w in [('دیجیکالا نقدی (%)',commission),('اضافه اعتباری دیجیکالا (%)',credit),('باسلام (%)',basalam)]:w.setRange(0,99.99);cf.addRow(caption,w)
 fee_page=page('پردازش اختصاصی دیجیکالا');ff=QFormLayout();fee_page.addLayout(ff);feecontrols={};inherit={}
 for key,caption in [('processing_percent','درصد مجموع پردازش'),('processing_min','کف مجموع پردازش (تومان)'),('processing_max','سقف مجموع پردازش (تومان)')]:
  row=QWidget();rl=QHBoxLayout(row);w=spin(0,key.endswith('percent'));check=QCheckBox('عمومی');check.toggled.connect(w.setDisabled);rl.addWidget(w);rl.addWidget(check);ff.addRow(caption,row);feecontrols[key]=w;inherit[key]=check
 inventory=page('موجودی / تنوع');it=table(['رنگ','سایز','موجودی واقعی','میانگین خرید واحد']);it.setMinimumHeight(225);inventory.addWidget(it,1);inventory.addWidget(QLabel('تغییر تعداد فقط اصلاح موجودی است؛ برای خرید جدید از ثبت خرید استفاده کنید.'))
 purchase=QPushButton('ثبت خرید و افزایش موجودی');inventory.addWidget(purchase);packs=QLineEdit();packs.setPlaceholderText('تعداد داخل مدل فروش جدید؛ مثلاً 5');inventory.addWidget(packs);newpack=QPushButton('افزودن مدل فروش');inventory.addWidget(newpack)
 addvariant=QPushButton('افزودن رنگ / سایز جدید');inventory.addWidget(addvariant)
 inventory_widget=tabs.widget(4);tabs.removeTab(4);inventory_scroll=QScrollArea();inventory_scroll.setWidgetResizable(True);inventory_scroll.setFrameShape(QScrollArea.NoFrame);inventory_scroll.setWidget(inventory_widget);tabs.addTab(inventory_scroll,'موجودی / تنوع')
 save=QPushButton('ثبت تغییرات سربرگ فعلی');l.addWidget(save);tabs.setEnabled(False);save.setEnabled(False)
 def choose(*_):
  item=listing.currentItem();p=next((p for p in app.data['active'] if item and item.checkState()==Qt.Checked and p['id']==item.data(Qt.UserRole)),None);selected['p']=p;tabs.setEnabled(bool(p));save.setEnabled(bool(p))
  if not p:return
  price_mode['value']='amount' if 'targetPriceOverride' in p else 'rate'
  name.setText(p['name']);supplier.setCurrentIndex(max(0,supplier.findData(p.get('supplierId'))));rate.blockSignals(True);amount.blockSignals(True);rate.setValue(E.effective_rate(app.data,p));amount.setValue(app.target(p));rate.blockSignals(False);amount.blockSignals(False);use_default.setChecked('profitRateOverride' not in p and 'targetPriceOverride' not in p)
  digi_enabled.setChecked(p.get('commission') is not None);basalam_enabled.setChecked(p.get('basalamCommission') is not None)
  commission.setValue(p.get('commission',0));credit.setValue(p.get('platformRate',0));basalam.setValue(p.get('basalamCommission',0))
  for key,w in feecontrols.items():w.setValue(E.fees(app.data,p)[key]);inherit[key].setChecked(key not in p.get('digiFeeOverride',{}));w.setDisabled(inherit[key].isChecked())
  m=E.mother(app.data,p);fill(it,[[v.get('color',''),v.get('size',''),v['stock'],round(v['averageCost'])] for v in m['variants']]);
  for r in range(it.rowCount()):it.item(r,3).setFlags(it.item(r,3).flags()&~Qt.ItemIsEditable)
  notice.setText('هر واحد فروش این ردیف شامل '+api['fa'](p['packSize'])+' واحد پایه است.')
 listing.currentItemChanged.connect(choose)
 def buy():
  if selected['p']:purchase_dialog(app,api,selected['p']);choose()
 purchase.clicked.connect(buy)
 def addpack(checked=False):
  try:
   p=selected['p']
   if not p:raise ValueError('ابتدا کالا را انتخاب کنید.')
   if not packs.text().strip():raise ValueError('تعداد داخل مدل فروش جدید را وارد کنید.')
   size=int(api['num'](packs.text()));assert size>0
   m=E.mother(app.data,p)
   if any(x.get('motherId')==m['id'] and x['packSize']==size for x in app.data['active']):raise ValueError('این مدل فروش وجود دارد.')
   fresh=package(app,m,size,api);fresh.update({key:copy.deepcopy(p[key]) for key in ['supplierId','commission','platformRate','basalamCommission'] if key in p});E.sync(app.data);app.baselines(fresh);fresh['initialPendingPrices']=['arazman'];app.persist();app.render();notice.setText('مدل فروش اضافه شد.')
  except (ValueError,AssertionError) as ex:notice.setText(str(ex) or 'عدد معتبر وارد کنید.')
 newpack.clicked.connect(addpack)
 def add_variant(checked=False):
  p=selected['p']
  if not p:return
  child,layout=app.dialog('افزودن رنگ / سایز');child.setParent(d,Qt.Dialog|Qt.FramelessWindowHint);child.resize(560,300);notice.clear();f=QFormLayout();layout.addLayout(f);color=QLineEdit();size=QLineEdit();f.addRow('رنگ',color);f.addRow('سایز',size);error=QLabel();layout.addWidget(error);button=QPushButton('ثبت تنوع');layout.addWidget(button)
  def save_variant():
   m=E.mother(app.data,p);key=(color.text().strip(),size.text().strip())
   if not any(key) or any((v.get('color',''),v.get('size',''))==key for v in m['variants']):error.setText('رنگ یا سایز جدید و غیرتکراری وارد کنید.');return
   m['variants'].append(dict(id=E.uid(),color=key[0],size=key[1],stock=0,averageCost=0));E.sync(app.data);app.persist();app.render();choose();child.accept()
  button.clicked.connect(save_variant);child.exec()
 addvariant.clicked.connect(add_variant)
 def commit():
  p=selected['p']
  if not p:return
  try:
   before=copy.deepcopy(p);index=tabs.currentIndex()
   if index==0:
    if not name.text().strip():raise ValueError('نام الزامی است.')
    p['name']=name.text().strip();p['supplierId']=supplier.currentData()
   elif index==1:
    p.pop('targetPriceOverride',None);p.pop('profitRateOverride',None)
    if not use_default.isChecked():
     if price_mode['value']=='amount':p['targetPriceOverride']=amount.value()
     else:p['profitRateOverride']=rate.value()
   elif index==2:
    if commission.value()+credit.value()>=100:raise ValueError('مجموع کمیسیون‌ها باید کمتر از ۱۰۰ باشد.')
    if digi_enabled.isChecked():p.update(commission=commission.value(),platformRate=credit.value())
    else:p.pop('commission',None);p.pop('platformRate',None)
    if basalam_enabled.isChecked():p['basalamCommission']=basalam.value()
    else:p.pop('basalamCommission',None)
    app.baselines(p)
   elif index==3:
    overrides={k:w.value() for k,w in feecontrols.items() if not inherit[k].isChecked()};cfg={**app.data['digiFees'],**overrides}
    if cfg['processing_min']>cfg['processing_max'] or not 0<=cfg['processing_percent']<100:raise ValueError('کف، سقف یا درصد پردازش معتبر نیست.')
    p['digiFeeOverride']=overrides
   else:
    m=E.mother(app.data,p);quantities={v['id']:int(api['num'](it.item(r,2).text())) for r,v in enumerate(m['variants'])}
    if any(q<0 for q in quantities.values()):raise ValueError('موجودی منفی مجاز نیست.')
    keys=[(it.item(r,0).text().strip(),it.item(r,1).text().strip()) for r in range(it.rowCount())]
    if len(set(keys))!=len(keys):raise ValueError('ترکیب رنگ و سایز تکراری است.')
    E.adjust(app.data,m,quantities)
    for r,v in enumerate(m['variants']):v['color'],v['size']=keys[r]
   app.history(p,'ویرایش کالا',before,copy.deepcopy(p));app.persist();app.render();choose();notice.setText('تغییرات ثبت شد.')
  except (ValueError,TypeError) as ex:notice.setText(str(ex))
 save.clicked.connect(commit);d.exec()

def sale_dialog(app,api,preset=None,existing=None):
 d,l=app.dialog('ویرایش فروش' if existing else 'ثبت فروش');d.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint);d.resize(980,660);l.addWidget(QLabel('تاریخ: '+api['fa'](api['jd'](existing['date'] if existing else api['today']()))));search,listing=app.product_picker(l);state={'p':None};f=QFormLayout();l.addLayout(f);q=spin(1);q.setMinimum(1);channel=QComboBox();price=QLineEdit();price.setPlaceholderText('اختیاری؛ قیمت جدول');f.addRow('تعداد بسته فروخته‌شده',q);f.addRow('نحوه فروش',channel);f.addRow('قیمت هر بسته (تومان)',price);summary=QLabel();summary.setWordWrap(True);l.addWidget(summary);t=table(['رنگ / سایز','موجودی واحد پایه','تعداد واحد پایه در این فروش']);l.addWidget(t);notice=QLabel();notice.setWordWrap(True);l.addWidget(notice);save=QPushButton('ثبت فروش');l.addWidget(save)
 def choose(*_):
  item=listing.currentItem();p=preset or next((p for p in app.data['active'] if item and item.checkState()==Qt.Checked and p['id']==item.data(Qt.UserRole)),None);state['p']=p;channel.clear();save.setEnabled(bool(p))
  if not p:t.setRowCount(0);return
  for c,title in api['CHANNELS'].items():
   if app.price(p,c) is not None:
    for mode in (['cash','credit'] if c in ['digikala','arazman'] else ['cash']):channel.addItem(title+(' — '+('نقدی' if mode=='cash' else 'اعتباری') if c in ['digikala','arazman'] else ''),c+'|'+mode)
  m=E.mother(app.data,p);previous={x['variantId']:x['quantity'] for x in existing['lines']} if existing else {};fill(t,[[E.label(v),api['fa'](v['stock']+previous.get(v['id'],0)),previous.get(v['id'],0)] for v in m['variants']]);
  for r in range(t.rowCount()):
   for c in [0,1]:t.item(r,c).setFlags(t.item(r,c).flags()&~Qt.ItemIsEditable)
  if existing:q.setValue(existing['quantity']);price.setText(str(existing['unitPrice']));channel.setCurrentIndex(max(0,channel.findData(existing['channel']+'|'+existing.get('settlementMode','cash'))))
  refresh()
 def refresh(*_):
  p=state['p'];choice=channel.currentData().split('|') if channel.currentData() else None
  if p and choice:
   needed=q.value()*p['packSize'];summary.setText('قیمت جدول: '+api['money'](app.price(p,choice[0]))+' | تعداد لازم: '+api['fa'](needed)+' واحد پایه')
   if t.rowCount()==1:t.item(0,2).setText(str(needed))
 channel.currentIndexChanged.connect(refresh);q.valueChanged.connect(refresh);listing.currentItemChanged.connect(choose)
 if preset:search.setText(preset['name']);search.setDisabled(True);listing.hide()
 choose()
 def commit():
  try:
   p=state['p'];choice=channel.currentData().split('|') if channel.currentData() else None
   if not p or not choice:raise ValueError('کالا و روش فروش را انتخاب کنید.')
   m=E.mother(app.data,p);alloc=[]
   for r,v in enumerate(m['variants']):
    count=int(api['num'](t.item(r,2).text()))
    if count<0:raise ValueError('تعداد منفی مجاز نیست.')
    if count:alloc.append(dict(variantId=v['id'],quantity=count))
   unit=int(api['num'](price.text())) if price.text().strip() else app.price(p,choice[0])
   if unit is None or unit<0:raise ValueError('قیمت معتبر نیست.')
   c,mode=choice;fees=copy.deepcopy(existing['feeSnapshot']) if existing else dict(commission=p.get('commission'),creditRate=p.get('platformRate',0),basalamCommission=p.get('basalamCommission'),digi=E.fees(app.data,p),arazmanRate=6.6)
   fees['platform']=fees.get('creditRate',0) if c=='digikala' and mode=='credit' else 0;fees['arazmanRate']=6.6 if mode=='credit' else 0
   sale=E.add_sale(app.data,p,q.value(),alloc,c,unit,fees,existing);sale.update(settlementMode=mode,manualPrice=bool(price.text().strip()));app.persist();app.render();d.accept();app.sale_notice(api['fa'](q.value())+' بسته «'+p['name']+'» فروخته شد')
  except (ValueError,TypeError) as ex:notice.setText(str(ex))
 save.clicked.connect(commit);d.exec()

def sale_channel(s,api):return api['CHANNELS'].get(s['channel'],s['channel'])+(' — '+('اعتباری' if s.get('settlementMode')=='credit' else 'نقدی') if s['channel'] in ['digikala','arazman'] else '')

def purchase_rows(app,api,start='0000',end='9999',mother_id=None):
 rows=[]
 for e in app.data['purchases']:
  if not start<=e['date']<=end or mother_id and e['motherId']!=mother_id:continue
  m=next(m for m in app.data['mothers'] if m['id']==e['motherId']);vs=E.variants(m);supplier=next((s['name'] for s in app.data['suppliers'] if s['id']==e.get('supplierId')),'—');q=sum(x['quantity'] for x in e['lines']);amount=sum(x['quantity']*x['unitCost'] for x in e['lines'])
  rows.append((e,[api['fa'](api['jd'](e['date'])),m['name'], '\n'.join(E.label(vs[x['variantId']])+': '+api['fa'](x['quantity'])+' × '+api['money'](x['unitCost']) for x in e['lines']),api['fa'](q),api['money'](amount),supplier,'لغوشده' if e.get('cancelled') else 'ثبت‌شده']))
 return sorted(rows,key=lambda x:x[0]['date'],reverse=True)

def purchase_panel(app,api,layout,mother_id=None):
 t=table(['انتخاب','تاریخ','کالای مادر','رنگ / سایز و خرید واحد','تعداد','مجموع خرید','مرجع','وضعیت']);t.setEditTriggers(QTableWidget.NoEditTriggers);layout.addWidget(t);actions=QHBoxLayout();layout.addLayout(actions);notice=QLabel();notice.setWordWrap(True);layout.addWidget(notice);chosen={'e':None};checks=[];period={'start':'0000','end':'9999'}
 def refresh(start=None,end=None):
  if start is not None:period.update(start=start,end=end)
  start,end=period['start'],period['end']
  rows=purchase_rows(app,api,start,end,mother_id);t.setRowCount(len(rows));chosen['e']=None;checks.clear();total=0
  for r,(e,vals) in enumerate(rows):
   check=QCheckBox();checks.append(check);t.setCellWidget(r,0,check)
   def select(checked,e=e,check=check):
    chosen['e']=e if checked else None
    if checked:
     for other in checks:
      if other is not check:other.blockSignals(True);other.setChecked(False);other.blockSignals(False)
   check.toggled.connect(select)
   for c,val in enumerate(vals,1):t.removeCellWidget(r,c);t.setItem(r,c,QTableWidgetItem(val))
   t.setRowHeight(r,70)
   if not e.get('cancelled'):total+=sum(x['quantity']*x['unitCost'] for x in e['lines'])
  make_copyable(t);notice.setText('مجموع خرید: '+api['money'](total));return total
 def add():
  p=next((p for p in app.data['active'] if p.get('motherId')==mother_id),None);purchase_dialog(app,api,p);refresh()
 def edit():
  e=chosen['e']
  if e and not e.get('cancelled'):purchase_dialog(app,api,existing=e);refresh()
 def cancel():
  e=chosen['e']
  if e and not e.get('cancelled') and app.yes('لغو خرید','خرید لغو شود؟ موجودی و میانگین خرید دوباره محاسبه می‌شوند.'):
   try:E.cancel_record(app.data,'purchases',e);app.persist();app.render();refresh()
   except ValueError as ex:notice.setText(str(ex))
 for title,fn in [('ثبت خرید',add),('ویرایش خرید',edit),('لغو خرید',cancel)]:b=QPushButton(title);b.clicked.connect(fn);actions.addWidget(b)
 refresh();return refresh

class Donut(QWidget):
 def __init__(self,parts,parent=None):super().__init__(parent);self.parts=parts;self.setMinimumSize(270,270)
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);rect=QRectF(30,30,self.width()-60,self.height()-60);size=min(rect.width(),rect.height());rect=QRectF((self.width()-size)/2,(self.height()-size)/2,size,size);total=sum(max(0,v) for _,v,_ in self.parts);angle=90*16
  for _,value,color in self.parts:
   span=round(max(0,value)/max(total,1)*360*16);p.setPen(QPen(QColor(color),36));p.drawArc(rect.adjusted(20,20,-20,-20),angle,-span);angle-=span
  p.setPen(self.palette().windowText().color());p.drawText(rect,Qt.AlignCenter,'ترکیب قیمت');p.end()

def breakdown(app,api,p,c,mode='cash'):
 price=app.price(p,c);cost=p['purchasePrice'];parts=[('قیمت خرید',cost,'#608ccc')];fees=[]
 if c=='digikala':
  cfg=E.fees(app.data,p);processing=min(cfg['processing_max'],max(cfg['processing_min'],api['rounded'](price*cfg['processing_percent']/100)));commission=api['rounded'](price*p['commission']/100);credit=api['rounded'](price*p.get('platformRate',0)/100) if mode=='credit' else 0;tax=api['rounded']((commission+credit+cfg['label_cost']+processing/2)*cfg['tax_percent']/100)
  fees=[('کمیسیون نقدی',commission,'#b57cc7'),('اضافه اعتباری',credit,'#e89c59'),('پردازش مشمول مالیات',processing/2,'#5cb9bc'),('پردازش غیرمشمول مالیات',processing/2,'#39949a'),('لیبل',cfg['label_cost'],'#cebb65'),('مالیات خدمات',tax,'#d47689')]
 elif c=='arazman':fees=[('کسر فروش اعتباری ۶٫۶٪',price*.066 if mode=='credit' else 0,'#b57cc7')]
 elif c=='basalam':fees=[('کمیسیون باسلام',price*p['basalamCommission']/100,'#b57cc7')]
 profit=price-cost-sum(v for _,v,_ in fees);parts+=fees+[('سود',profit,'#43a575')];return price,parts

def price_details(app,api,p,c):
 if c not in ['digikala','arazman','basalam']:return
 d,l=app.dialog('جزئیات قیمت '+api['CHANNELS'][c]);d.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint);d.resize(820,620);mode=QComboBox();mode.addItem('نقدی','cash');mode.addItem('اعتباری','credit');mode.setCurrentIndex(1 if c=='arazman' else 0);mode.setVisible(c!='basalam');l.addWidget(mode);body=QWidget();bl=QHBoxLayout(body);l.addWidget(body);note=QLabel();note.setWordWrap(True);l.addWidget(note)
 def refresh():
  while bl.count():
   w=bl.takeAt(0).widget()
   if w:w.deleteLater()
  price,parts=breakdown(app,api,p,c,mode.currentData());bl.addWidget(Donut(parts));legend=QWidget();f=QFormLayout(legend)
  for title,value,color in parts:
   v=QLabel(api['money'](value)+' — '+api['fa'](round(value/max(price,1)*100,2))+'٪');v.setStyleSheet('color:'+color+';font-weight:bold;');f.addRow(title,v)
  bl.addWidget(legend);text='قیمت فروش: '+api['money'](price)+'\n'
  if c=='digikala':
   cfg=E.fees(app.data,p);text+='پردازش '+api['fa'](cfg['processing_percent'])+'٪، کف '+api['money'](cfg['processing_min'])+'، سقف '+api['money'](cfg['processing_max'])+'؛ '+('با تنظیمات اختصاصی کالا' if p.get('digiFeeOverride') else 'با تنظیمات عمومی')+'\nمالیات بر کمیسیون‌ها، لیبل و نصف پردازش محاسبه می‌شود.'
  if any(v<0 for _,v,_ in parts):text+='\nسود منفی است؛ مقدار منفی در راهنما آمده و در نمودار سهم مثبت ندارد.'
  if c=='digikala':
   text+='\n'+ ' | '.join(caption+': '+('اختصاصی' if key in p.get('digiFeeOverride',{}) else 'عمومی') for key,caption in [('processing_percent','درصد'),('processing_min','کف'),('processing_max','سقف')])
  note.setText(text)
 mode.currentIndexChanged.connect(refresh);refresh();d.exec()

def product_report(app,api,p):
 d,l=app.dialog('گزارش '+p['name']);d.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint);d.resize(1180,710);tabs=QTabWidget();tabs.setObjectName('settingsTabs');l.addWidget(tabs);m=E.mother(app.data,p);sales=[s for s in app.data['sales'] if s['productId']==p['id']];active=[s for s in sales if not s.get('cancelled')];page=QWidget();pl=QVBoxLayout(page);cards=QHBoxLayout();pl.addLayout(cards);card_values={}
 total_buy=sum(x['quantity']*x['unitCost'] for e in app.data['purchases'] if e['motherId']==m['id'] and not e.get('cancelled') for x in e['lines'])
 for title,value in [('مجموع سود فروش',api['money'](sum(app.profit(s) or 0 for s in active))),('مجموع فروش',api['money'](sum(s['totalPrice'] for s in active))),('مجموع قیمت خرید کالای مادر',api['money'](total_buy)),('تعداد بسته فروخته‌شده',api['fa'](sum(s['quantity'] for s in active)))]:
  card=QWidget();card.setObjectName('productSearchGroup');cl=QVBoxLayout(card);cl.addWidget(QLabel(title));number=QLabel(value);card_values[title]=number;number.setStyleSheet('font-size:18px;font-weight:bold;');cl.addWidget(number);cards.addWidget(card)
  if title=='مجموع سود فروش':card.setStyleSheet('background:rgba(50,170,100,35);border-radius:12px;')
 stock=table(['رنگ','سایز','موجودی واحد پایه','میانگین خرید هر واحد']);fill(stock,[[v.get('color',''),v.get('size',''),api['fa'](v['stock']),api['money'](v['averageCost'])] for v in m['variants']]);stock.setEditTriggers(QTableWidget.NoEditTriggers);pl.addWidget(stock);pl.addWidget(QLabel('موجودی مشترک کالای مادر: '+m['name']+' | هر بسته این مدل: '+api['fa'](p['packSize'])+' واحد'));tabs.addTab(page,'خلاصه کالا')
 sp=QWidget();sl=QVBoxLayout(sp);st=table(['انتخاب','تاریخ','روش فروش','بسته / واحد پایه','تنوع فروخته‌شده','خرید هر بسته','فروش هر بسته','سود کل','وضعیت']);st.setEditTriggers(QTableWidget.NoEditTriggers);sl.addWidget(st);actions=QHBoxLayout();sl.addLayout(actions);chosen={'s':None};notice=QLabel();notice.setWordWrap(True);sl.addWidget(notice)
 def refresh():
  st.setRowCount(len(sales));checks=[];vs=E.variants(m)
  for r,s in enumerate(sales):
   check=QCheckBox();checks.append(check);st.setCellWidget(r,0,check)
   def pick(checked,s=s,check=check):
    chosen['s']=s if checked else None
    if checked:
     for other in checks:
      if other is not check:other.blockSignals(True);other.setChecked(False);other.blockSignals(False)
   check.toggled.connect(pick);vals=[api['fa'](api['jd'](s['date'])),sale_channel(s,api),api['fa'](s['quantity'])+' / '+api['fa'](s['quantity']*s['packSize']),'\n'.join(E.label(vs[x['variantId']])+': '+api['fa'](x['quantity']) for x in s['lines']),api['money'](s['purchasePriceAtSale']),api['money'](s['unitPrice']),api['money'](app.profit(s)),'لغوشده' if s.get('cancelled') else 'ثبت‌شده']
   for c,val in enumerate(vals,1):
    item=QTableWidgetItem(val)
    if s.get('cancelled'):item.setBackground(QColor(220,70,80,35))
    st.removeCellWidget(r,c);st.setItem(r,c,item)
   st.setRowHeight(r,74)
  make_copyable(st)
 def edit():
  s=chosen['s']
  if s and not s.get('cancelled'):sale_dialog(app,api,p,s);refresh()
 def cancel():
  s=chosen['s']
  if s and not s.get('cancelled') and app.yes('لغو فروش','واحدهای فروخته‌شده به همان رنگ و سایز برگردند؟'):
   try:E.cancel_record(app.data,'sales',s);app.history(p,'لغو فروش',s['totalPrice'],None);app.persist();app.render();refresh()
   except ValueError as ex:notice.setText(str(ex))
 for title,fn in [('ویرایش فروش',edit),('لغو فروش',cancel)]:b=QPushButton(title);b.clicked.connect(fn);actions.addWidget(b)
 refresh();tabs.addTab(sp,'تاریخچه فروش');bp=QWidget();purchase_panel(app,api,QVBoxLayout(bp),m['id']);tabs.addTab(bp,'موجودی و خرید');ht=table(['تاریخ','نوع تغییر','قبل','بعد'])
 names={'name':'نام','stock':'موجودی بسته','purchasePrice':'قیمت خرید','profitRateOverride':'درصد سود','targetPriceOverride':'قیمت دلخواه','commission':'کمیسیون نقدی','platformRate':'کمیسیون اضافه اعتباری','basalamCommission':'کمیسیون باسلام','digiFeeOverride':'پردازش اختصاصی'}
 def display(v):
  if isinstance(v,dict):return '\n'.join(names[k]+': '+(api['money'](value) if k in ['purchasePrice','targetPriceOverride'] else api['fa'](value)) for k,value in v.items() if k in names)
  return '—' if v is None else api['fa'](v)
 fill(ht,[[api['fa'](api['jd'](e['date'])),e['label'],display(e.get('before')),display(e.get('after'))] for e in reversed(app.data['history']) if e['productId']==p['id']]);ht.setEditTriggers(QTableWidget.NoEditTriggers);tabs.addTab(ht,'تاریخچه تغییرات')
 def refresh_summary(*_):
  current=[s for s in sales if not s.get('cancelled')];buy_total=sum(x['quantity']*x['unitCost'] for e in app.data['purchases'] if e['motherId']==m['id'] and not e.get('cancelled') for x in e['lines']);values=[api['money'](sum(app.profit(s) or 0 for s in current)),api['money'](sum(s['totalPrice'] for s in current)),api['money'](buy_total),api['fa'](sum(s['quantity'] for s in current))]
  for widget,value in zip(card_values.values(),values):widget.setText(value)
  fill(stock,[[v.get('color',''),v.get('size',''),api['fa'](v['stock']),api['money'](v['averageCost'])] for v in m['variants']])
 tabs.currentChanged.connect(refresh_summary);d.exec()

def make_copyable(t):
 if t.editTriggers()!=QTableWidget.NoEditTriggers or t.property('keepItemSelection'):return
 for r in range(t.rowCount()):
  for c in range(t.columnCount()):
   item=t.item(r,c)
   if item and not t.cellWidget(r,c):
    label=QLabel(item.text());label.setTextFormat(Qt.PlainText);label.setWordWrap(True);label.setAlignment(Qt.AlignCenter);label.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard)
    if item.background().style()!=Qt.NoBrush:label.setStyleSheet('background:'+item.background().color().name(QColor.HexArgb)+';')
    t.setCellWidget(r,c,label)

class CopySupport(QObject):
 def eventFilter(self,obj,event):
  if event.type()==QEvent.Show and isinstance(obj,QTableWidget):make_copyable(obj)
  if event.type()==QEvent.Show and isinstance(obj,QPushButton):obj.setAutoDefault(False);obj.setDefault(False)
  if event.type()==QEvent.Show and isinstance(obj,QLabel):obj.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard)
  if event.type()==QEvent.ContextMenu and isinstance(obj,(QPushButton,QLabel,QTableWidget)):
   text=obj.text() if isinstance(obj,(QPushButton,QLabel)) else '\n'.join(i.text() for i in obj.selectedItems())
   if not text and isinstance(obj,QTableWidget):
    i=obj.itemAt(obj.viewport().mapFromGlobal(event.globalPos()));text=i.text() if i else ''
   if text:
    menu=QMenu(obj);action=menu.addAction('کپی');action.triggered.connect(lambda:QApplication.clipboard().setText(text));menu.exec(event.globalPos());return True
  return False

def install(App,api):
 App.inventory_api=api
 original_init=App.__init__;original_render=App.render
 def init(self):
  original_init(self);self.copy_support=CopySupport(self);QApplication.instance().installEventFilter(self.copy_support)
  for label in self.findChildren(QLabel):label.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard)
  self.render()
 App.__init__=init
 App.target=lambda self,p:E.target(self.data,p)
 def price(self,p,c):
  if c=='digikala':return None if p.get('commission') is None else api['solve'](self.target(p),p['commission'],0,E.fees(self.data,p))
  if c=='arazman':return math.ceil(self.target(p)/.934)
  if c=='basalam':return None if p.get('basalamCommission') is None else math.ceil(self.target(p)/(1-p['basalamCommission']/100))
  if c=='inperson' or c in api['SOCIAL'] and p.get('publishedChannels',{}).get(c):return self.target(p)
  return p.get(c+'Price')
 App.price=price
 def baselines(self,p):
  p.setdefault('confirmedPrices',{});p.setdefault('confirmedTargets',{})
  for c in api['CHANNELS']:
   v=self.price(p,c)
   if v is not None:
    if c=='digikala':p.setdefault('digiConfirmedPrice',v)
    else:p['confirmedPrices'].setdefault(c,v)
    p['confirmedTargets'].setdefault(c,self.target(p))
 App.baselines=baselines
 original_pending=App.pending_price
 def pending(self,p,c):
  return original_pending(self,p,c) or self.price(p,c) is not None and c in ['digikala','arazman','basalam','snappshop'] and p.get('confirmedTargets',{}).get(c,self.target(p))!=self.target(p)
 App.pending_price=pending
 def confirm(self,p,c):
  new=self.price(p,c);old=p.get('digiConfirmedPrice') if c=='digikala' else p.get('confirmedPrices',{}).get(c)
  if self.yes('تأیید اصلاح قیمت','قیمت قبلی: '+api['money'](old)+'\nقیمت جدید: '+api['money'](new)+'\nآیا در '+api['CHANNELS'][c]+' اصلاح کرده‌اید؟'):
   if c=='digikala':p['digiConfirmedPrice']=new
   else:p.setdefault('confirmedPrices',{})[c]=new
   p.setdefault('confirmedTargets',{})[c]=self.target(p);p['initialPendingPrices']=[x for x in p.get('initialPendingPrices',[]) if x!=c];self.history(p,'تأیید قیمت '+api['CHANNELS'][c],old,new);self.persist();self.render()
 App.confirm_price=confirm
 def commission(self,p):
  d,l=self.dialog('کمیسیون دیجیکالا');f=QFormLayout();l.addLayout(f);cash=spin(p.get('commission',0),True);cash.setRange(0,99.99);credit=spin(p.get('platformRate',0),True);credit.setRange(0,99.99);f.addRow('کمیسیون نقدی (%)',cash);f.addRow('اضافه اعتباری (%)',credit);notice=QLabel();l.addWidget(notice);save=QPushButton('ثبت کمیسیون');l.addWidget(save)
  def commit():
   if cash.value()+credit.value()>=100:notice.setText('مجموع کمیسیون‌ها باید کمتر از ۱۰۰ باشد.');return
   old=p.get('commission');p.update(commission=cash.value(),platformRate=credit.value());self.baselines(p);self.history(p,'کمیسیون',old,p['commission']);self.persist();self.render();d.accept()
  save.clicked.connect(commit);d.exec()
 App.commission=commission
 def cell(self,r,c,text,color=None):
  label=QLabel(text);label.setTextFormat(Qt.PlainText);label.setAlignment(Qt.AlignCenter);label.setWordWrap(True);label.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard);label.setStyleSheet('background:transparent;'+('color:'+color+';' if color else ''));self.table.setCellWidget(r,c,label)
 App.cell=cell
 def render(self):
  E.sync(self.data);original_render(self);entries=self.data['deleted'] if self.mode=='deleted' else self.data['active'];entries=[p for p in entries if api['matches'](p['name'],self.search.text()) and (not self.pending or any(self.pending_price(p,c) for c in api['CHANNELS']))];pages=max(1,math.ceil(len(entries)/10))
  for r,p in enumerate(entries[self.page*10:self.page*10+10]):
   stock=QWidget();vl=QVBoxLayout(stock);vl.setContentsMargins(2,2,2,2);vl.setSpacing(2);count=QLabel(api['fa'](p['stock']));count.setAlignment(Qt.AlignCenter);count.setProperty('stockPrimary',True);count.setStyleSheet('font-size:19px;font-weight:700;background:transparent;');small=QLabel(api['fa'](round(E.effective_rate(self.data,p),2))+'٪');small.setProperty('stockSecondary',True);small.setAlignment(Qt.AlignCenter);small.setStyleSheet('font-size:9px;background:transparent;');vl.addWidget(count);vl.addWidget(small);self.table.setCellWidget(r,3,stock)
   for col,c in enumerate(api['CHANNELS'],5):
    v=self.price(p,c)
    if v is None:continue
    if c not in ['digikala','arazman','basalam'] and not self.pending_price(p,c):continue
    holder=QWidget();holder.setStyleSheet('background:'+api['THEMES'][self.data['theme']][1]+';');hl=QHBoxLayout(holder);hl.setContentsMargins(0,0,0,0);hl.setSpacing(1);from price_visuals import PriceSurface
    button=PriceSurface(api['money'](v),self.data['theme'],api['THEMES'],self.pending_price(p,c));button.clicked.connect(lambda checked=False,p=p,c=c:__import__('price_visuals').show_details(self,api,p,c));hl.addWidget(button,1)
    if self.pending_price(p,c):
     tick=QPushButton('✓');tick.setFixedWidth(23);tick.setStyleSheet('padding:3px 0;');tick.setObjectName('pendingPrice');tick.clicked.connect(lambda checked=False,p=p,c=c:self.confirm_price(p,c));hl.addWidget(tick)
    if c in ['digikala','arazman','basalam']:
     _,parts=breakdown(self,api,p,c,'credit' if c=='arazman' else 'cash');button.setToolTip('\n'.join(title+': '+api['money'](value) for title,value,_ in parts)+'\nبرای نمودار و شرح کلیک کنید')
    self.table.setCellWidget(r,col,holder)
  pager=self.page_label.parentWidget().layout()
  if not hasattr(self,'direct_page'):
   self.direct_page=QLineEdit();self.direct_page.setPlaceholderText('شماره صفحه');self.direct_page.setFixedWidth(95);self.direct_page.returnPressed.connect(lambda:go());pager.addWidget(self.direct_page);self.near_pages=QWidget();self.near_layout=QHBoxLayout(self.near_pages);self.near_layout.setContentsMargins(0,0,0,0);pager.addWidget(self.near_pages)
  def go():
   try:self.page=max(0,min(pages-1,int(api['num'](self.direct_page.text()))-1));self.render()
   except ValueError:pass
  # Refresh connection each render so the current filtered page count is used.
  self.direct_page.returnPressed.disconnect();self.direct_page.returnPressed.connect(go)
  while self.near_layout.count():self.near_layout.takeAt(0).widget().deleteLater()
  numbers=sorted(set([0,pages-1]+list(range(max(0,self.page-1),min(pages,self.page+2)))))
  previous=-1
  for n in numbers:
   if previous>=0 and n-previous>1:self.near_layout.addWidget(QLabel('…'))
   b=QPushButton(api['fa'](n+1));b.setFixedSize(32,34);b.setCheckable(True);b.setChecked(n==self.page);b.setStyleSheet('padding:6px;min-width:20px;');b.clicked.connect(lambda checked=False,n=n:(setattr(self,'page',n),self.render()));self.near_layout.addWidget(b);previous=n
 App.render=render
 App.add=lambda self:add_product(self,api);App.edit=lambda self:edit_product(self,api);App.sell=lambda self:sale_dialog(self,api);App.sale_form=lambda self,p,sale=None:sale_dialog(self,api,p,sale);App.report=lambda self,p:product_report(self,api,p)
 def purge(self,p):
  if p not in self.data['deleted']:return
  mother_id=p['motherId'];remaining=[x for x in self.data['active']+self.data['deleted'] if x['id']!=p['id'] and x.get('motherId')==mother_id]
  self.data['deleted'].remove(p)
  if remaining:
   # Preserve physical removals anonymously when another listing shares the stock.
   for sale in self.data['sales']:
    if sale['productId']==p['id'] and not sale.get('cancelled'):
     self.data['inventoryAdjustments'].append(dict(id=sale['id'],motherId=mother_id,kind='adjust',date=sale['date'],createdAt=sale['createdAt'],lines=[dict(variantId=line['variantId'],quantity=-line['quantity']) for line in sale['lines']]))
   self.data['sales']=[sale for sale in self.data['sales'] if sale['productId']!=p['id']]
  else:
   for key in ['sales','purchases','inventoryAdjustments']:self.data[key]=[e for e in self.data[key] if e.get('motherId')!=mother_id]
   self.data['mothers']=[m for m in self.data['mothers'] if m['id']!=mother_id]
  self.data['history']=[e for e in self.data['history'] if e['productId']!=p['id']];E.sync(self.data);self.persist();self.render()
 App.purge_product=purge
