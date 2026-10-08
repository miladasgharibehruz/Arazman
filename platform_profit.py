"""Per-platform target editor; prices are net of platform fees."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QLabel,QCheckBox,QTabWidget
import inventory_engine as E
CHANNELS=('digikala','arazman','basalam')
class PlatformProfitEditor(QWidget):
 def __init__(self,app,api,spin):
  super().__init__();self.app=app;self.api=api;self.product=None;self.controls={}
  layout=QVBoxLayout(self);note=QLabel('مبلغ هدف، دریافتی پس از کسورات است: قیمت خرید + سود. آخرین کادر تغییرکرده مبنای محاسبه می‌شود.');note.setWordWrap(True);layout.addWidget(note)
  tabs=QTabWidget();tabs.setObjectName('settingsTabs');layout.addWidget(tabs)
  for channel in CHANNELS:
   page=QWidget();form=QFormLayout(page);inherit=QCheckBox('استفاده از سود اصلی کالا');rate=spin(0,True);rate.setRange(-100,10000);rate.setDecimals(4);amount=spin();preview=QLabel();preview.setWordWrap(True)
   form.addRow(inherit);form.addRow('درصد سود روی قیمت خرید',rate);form.addRow('مبلغ هدف پس از کسورات (تومان)',amount);form.addRow(preview);tabs.addTab(page,api['CHANNELS'][channel]);self.controls[channel]=dict(inherit=inherit,rate=rate,amount=amount,preview=preview,mode='rate')
   rate.valueChanged.connect(lambda value,c=channel:self.changed(c,'rate',value));amount.valueChanged.connect(lambda value,c=channel:self.changed(c,'amount',value));inherit.toggled.connect(lambda checked,c=channel:self.inherit_changed(c,checked))
 def changed(self,c,mode,value):
  if not self.product:return
  controls=self.controls[c];cost=self.product['purchasePrice'];other=controls['amount'] if mode=='rate' else controls['rate'];other.blockSignals(True);other.setValue(round(cost*(1+value/100)) if mode=='rate' else (value/cost-1)*100 if cost else 0);other.blockSignals(False);controls['mode']=mode;self.preview(c)
 def inherit_changed(self,c,checked):
  controls=self.controls[c]
  for key in ['rate','amount']:controls[key].setDisabled(checked)
  if checked and self.product:
   for key,value in [('rate',E.effective_rate(self.app.data,self.product)),('amount',E.target(self.app.data,self.product))]:controls[key].blockSignals(True);controls[key].setValue(value);controls[key].blockSignals(False)
  self.preview(c)
 def preview(self,c):
  controls=self.controls[c];controls['preview'].setText('مبلغ سود هدف: '+self.api['money'](controls['amount'].value()-(self.product or {}).get('purchasePrice',0)))
 def load(self,p):
  self.product=p
  for c,controls in self.controls.items():
   override=p.get('platformProfitOverrides',{}).get(c,{})
   controls['mode']='amount' if 'amount' in override else 'rate'
   for key,value in [('rate',E.channel_rate(self.app.data,p,c)),('amount',E.channel_target(self.app.data,p,c))]:controls[key].blockSignals(True);controls[key].setValue(value);controls[key].blockSignals(False)
   controls['inherit'].blockSignals(True);controls['inherit'].setChecked(not override);controls['inherit'].blockSignals(False)
   for key in ['rate','amount']:controls[key].setDisabled(not override)
   self.preview(c)
 def save(self,p):
  overrides=dict(p.get('platformProfitOverrides',{}))
  for c,controls in self.controls.items():
   if controls['inherit'].isChecked():overrides.pop(c,None)
   else:mode=controls['mode'];overrides[c]={mode:controls[mode].value()}
  if overrides:p['platformProfitOverrides']=overrides
  else:p.pop('platformProfitOverrides',None)
