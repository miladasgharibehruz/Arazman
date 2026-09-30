"""Native Windows desktop price monitor. Python 3.11+, PySide6, jdatetime."""
import sys, json, math, uuid, os, re, copy
from pathlib import Path
from datetime import datetime, date
import jdatetime
from update_support import build_update_tab, VERSION
from PySide6.QtCore import Qt, QTimer, QObject, QEvent, QRectF, QPropertyAnimation
from PySide6.QtGui import QColor, QIcon, QPainter, QLinearGradient, QFont, QPen, QBrush, QFontDatabase, QPixmap
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,QTableWidget,QTableWidgetItem,QHeaderView,QDialog,QFormLayout,QDialogButtonBox,QMessageBox,QComboBox,QSpinBox,QDoubleSpinBox,QLabel,QTabWidget,QTextEdit,QGridLayout,QGraphicsDropShadowEffect,QSizePolicy,QAbstractSpinBox,QScrollArea,QListWidget,QListWidgetItem,QCheckBox,QGraphicsOpacityEffect,QButtonGroup)
ROOT=Path(os.getenv('LOCALAPPDATA',str(Path.home()))) / 'ArazmanPriceMonitor'
ROOT.mkdir(parents=True,exist_ok=True)
FILE=ROOT/'data.json'
CHANNELS={'digikala':'دیجیکالا','arazman':'آرازمان','basalam':'باسلام','snappshop':'اسنپ شاپ','inperson':'حضوری','instagram':'اینستاگرام','rubika':'روبیکا','telegram':'تلگرام','bale':'بله'}
SOCIAL=['instagram','rubika','telegram','bale']
HEAD=['ردیف','نام کالا','قیمت خرید','موجودی','قیمت فروش با سود خرید','دیجیکالا','آرازمان(ترب)','باسلام','اسنپ شاپ','حضوری','اینستاگرام','روبیکا','تلگرام','بله','وضعیت','گزارش']
FEES=dict(processing_percent=7,processing_min=36000,processing_max=240000,label_cost=6000,tax_percent=10)
THEMES={'روشن و مینیمال':('#f3f6fb','#ffffff','#172b4d','#1565d8','#d8e2ef'),'سرمه‌ای و مسی':('#071526','#11243a','#edf3fa','#bf8058','#354c65'),'تیره و نئونی':('#090f16','#131d28','#e0f6ff','#00b5d4','#314550'),'کرم و زیتونی':('#f6f3e9','#fffdf6','#303927','#68764d','#dedfcd')}
def num(v): return str(v).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789')).replace(',','').replace('٬','').replace('٫','.')
def fa(v): return str(v).translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'))
def money(v): return '—' if v is None else fa(f'{v:,.0f}')+' تومان'
def norm(v): return re.sub('[ًٌٍَُِّْـ‌]','',v.lower().replace('ي','ی').replace('ك','ک'))
def matches(name,q): return not q or any(w.startswith(norm(q)) for w in re.split(r'\W+',norm(name)))
def today(): return date.today().isoformat()
def jd(v): return jdatetime.date.fromgregorian(date=date.fromisoformat(v)).strftime('%Y/%m/%d')
def rounded(v): return math.floor(v+0.5)
def net(price,commission,platform,cfg):
 combined=min(cfg['processing_max'],max(cfg['processing_min'],rounded(price*cfg['processing_percent']/100)))
 c=rounded(price*commission/100);p=rounded(price*platform/100);tax=rounded((c+p+cfg['label_cost']+combined/2)*cfg['tax_percent']/100)
 return price-c-p-cfg['label_cost']-combined-tax

def solve(target,commission,platform,cfg):
 lo=0;hi=max(1,target)
 while net(hi,commission,platform,cfg)<target:
  hi*=2
  if hi>10**13:return None
 while lo<hi:
  mid=(lo+hi)//2
  if net(mid,commission,platform,cfg)>=target:hi=mid
  else:lo=mid+1
 return lo
class NeonHover(QObject):
 def eventFilter(self,obj,event):
  if isinstance(obj,QPushButton) and not isinstance(obj,AnimatedLogo):
   if event.type()==QEvent.Enter and obj.isEnabled():
    glow=QGraphicsDropShadowEffect(obj);glow.setOffset(0,0);glow.setBlurRadius(24);glow.setColor(QColor(obj.property('glowColor') or QApplication.instance().property('accentColor') or '#1565d8'));obj.setGraphicsEffect(glow)
   elif event.type()==QEvent.Leave:obj.setGraphicsEffect(None)
  return False
class AnimatedLogo(QPushButton):
 def __init__(self,parent=None):
  super().__init__(parent);self.setFixedSize(320,108);self.setCursor(Qt.PointingHandCursor);self.setToolTip('بازگشت به صفحه اصلی');self.phase=0;self.hovered=False;self.accent='#1565d8';self.setAccessibleName('Arazman — صفحه اصلی');self.timer=QTimer(self);self.timer.timeout.connect(self.animate);self.timer.start(40)
 def animate(self):self.phase=(self.phase+0.018)%(2*math.pi);self.update()
 def enterEvent(self,e):self.hovered=True;self.update();super().enterEvent(e)
 def leaveEvent(self,e):self.hovered=False;self.update();super().leaveEvent(e)
 def paintEvent(self,e):
  painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);color=QColor(self.accent);font=QFont('Segoe UI',36,QFont.Bold);painter.setFont(font)
  rect=QRectF(10,6,self.width()-20,79);shift=(math.sin(self.phase)+1)/2;gradient=QLinearGradient(-160+shift*420,0,180+shift*420,0);gradient.setColorAt(0,color);gradient.setColorAt(.5,color.lighter(180));gradient.setColorAt(1,color);painter.setPen(QPen(QBrush(gradient),1));painter.drawText(rect,Qt.AlignCenter,'Arazman')
  painter.setPen(QPen(color.lighter(140) if self.hovered else color,3));width=110+35*math.sin(self.phase);painter.drawLine(int((self.width()-width)/2),91,int((self.width()+width)/2),91);painter.end()
class PlatformHeader(QHeaderView):
 def __init__(self,parent):
  super().__init__(Qt.Horizontal,parent);self.setMouseTracking(True);self.setSectionsClickable(False);self.setMinimumHeight(58);self.hover_section=-1;self.tick=0;self.icons={};self.bg='#1565d8';self.fg='#ffffff'
  base=Path(__file__).resolve().parent/'icons'
  for i,c in enumerate(CHANNELS,5):
   icon=QPixmap(str(base/(c+'.img')))
   if not icon.isNull():
    if c=='snappshop':icon=icon.copy(359,20,1082,954)
    elif c=='inperson':icon=icon.copy(210,29,1314,883)
    self.icons[i]=icon
  self.motion=QTimer(self);self.motion.timeout.connect(self.advance)
 def mouseMoveEvent(self,e):
  section=self.logicalIndexAt(e.position().toPoint())
  if section!=self.hover_section:self.hover_section=section;self.tick=0;self.motion.start(35);self.viewport().update()
  super().mouseMoveEvent(e)
 def leaveEvent(self,e):self.hover_section=-1;self.motion.stop();self.viewport().update();super().leaveEvent(e)
 def advance(self):
  self.tick+=1;self.viewport().update()
  if self.tick>=16:self.motion.stop()
 def paintSection(self,painter,rect,index):
  painter.save();painter.fillRect(rect,QColor(self.bg));painter.setPen(QColor(self.fg));font=QFont('Vazirmatn',11);font.setBold(True);painter.setFont(font);label=str(self.model().headerData(index,Qt.Horizontal) or '')
  icon=self.icons.get(index);textrect=QRectF(rect).adjusted(4,3,-4,-3)
  if icon:
   offset=2*math.sin(self.tick*.7) if index==self.hover_section and self.tick<16 else 0
   displayed=icon.scaled(28,18,Qt.KeepAspectRatio,Qt.SmoothTransformation)
   x=rect.center().x()-displayed.width()/2;y=rect.top()+14-displayed.height()/2+offset
   painter.drawPixmap(int(x),int(y),displayed);textrect.setTop(rect.top()+25)
  elif index==9:
   painter.drawText(QRectF(rect.left(),rect.top()+2,rect.width(),20),Qt.AlignCenter,'▣');textrect.setTop(rect.top()+25)
  painter.drawText(textrect,Qt.AlignCenter|Qt.TextWordWrap,label);painter.restore()
class ThemedDialog(QDialog):
 def __init__(self,parent,title):
  self.close_only_with_x=title in ['افزودن کالا','ویرایش کالا','انتخاب کالا با نام یا شماره']
  flags=(Qt.Dialog if self.close_only_with_x else Qt.Popup)|Qt.FramelessWindowHint
  super().__init__(parent,flags);self.setWindowTitle(title);self.setObjectName('settingsWindow');self.setMinimumWidth(500);self.setLayoutDirection(Qt.RightToLeft)
  outer=QVBoxLayout(self);outer.setContentsMargins(1,1,1,1);outer.setSpacing(0)
  bar=QWidget();bar.setObjectName('settingsTitle');bar.setFixedHeight(48);row=QHBoxLayout(bar);row.setContentsMargins(16,8,12,8);label=QLabel(title);label.setWordWrap(True);label.setObjectName('settingsTitleLabel');row.addWidget(label,1);close=QPushButton('×');close.setObjectName('settingsClose');close.setFixedSize(34,32);close.clicked.connect(self.reject);row.addWidget(close);outer.addWidget(bar)
  content=QWidget();self.content_layout=QVBoxLayout(content);self.content_layout.setContentsMargins(22,20,22,20);self.content_layout.setSpacing(14);outer.addWidget(content)
 def showEvent(self,event):
  super().showEvent(event)
  if self.close_only_with_x:
   for box in self.findChildren(QDialogButtonBox):
    cancel=box.button(QDialogButtonBox.Cancel)
    if cancel:cancel.hide()
  if self.parentWidget():self.move(self.parentWidget().mapToGlobal(self.parentWidget().rect().center())-self.rect().center())
 def keyPressEvent(self,event):
  if self.close_only_with_x and event.key()==Qt.Key_Escape:event.ignore();return
  super().keyPressEvent(event)
class PersianCalendar(QDialog):
 def __init__(self,parent):
  super().__init__(parent);self.setWindowTitle('انتخاب تاریخ شمسی');self.value=today();self.anchor=jdatetime.date.today().replace(day=1);self.setFixedHeight(260);self.layout=QVBoxLayout(self);self.layout.setContentsMargins(8,6,8,6);self.layout.setSpacing(4);self.draw()
 def draw(self):
  while self.layout.count():
   w=self.layout.takeAt(0).widget()
   if w:w.deleteLater()
  top=QWidget();top.setFixedHeight(40);row=QHBoxLayout(top);row.setContentsMargins(0,0,0,0)
  for label,delta in [('ماه قبل',-1),(fa(['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'][self.anchor.month-1]+' '+str(self.anchor.year)),0),('ماه بعد',1)]:
   b=QPushButton(label);b.clicked.connect(lambda checked=False,d=delta:self.move(d));row.addWidget(b)
  self.layout.addWidget(top);box=QWidget();grid=QGridLayout(box);grid.setContentsMargins(0,0,0,0);grid.setSpacing(3)
  for row_index in range(1,7):grid.setRowMinimumHeight(row_index,28)
  for column_index in range(7):grid.setColumnStretch(column_index,1)
  for i,n in enumerate(['ش','ی','د','س','چ','پ','ج']):grid.addWidget(QLabel(n),0,i)
  for d in range(1,32):
   try:x=self.anchor.replace(day=d)
   except ValueError:break
   idx=self.anchor.weekday()+d-1;b=QPushButton(fa(d));b.setFixedHeight(28);b.setStyleSheet('padding:2px;');b.clicked.connect(lambda checked=False,x=x:self.choose(x));grid.addWidget(b,idx//7+1,idx%7)
  self.layout.addWidget(box)
 def move(self,d):
  m=self.anchor.month-1+d;y=self.anchor.year+m//12;self.anchor=jdatetime.date(y,m%12+1,1);self.draw()
 def choose(self,x):
  self.value=x.togregorian().isoformat()
  if self.value>today():QMessageBox.warning(self,'تاریخ','تاریخ آینده مجاز نیست.');return
  self.accept()
class App(QMainWindow):
 def __init__(self):
  super().__init__();self.setWindowTitle('Arazman');self.resize(1500,850)
  try:self.data=json.loads(FILE.read_text(encoding='utf8'))
  except (OSError,ValueError):self.data={}
  for k,v in dict(active=[],deleted=[],sales=[],stockEvents=[],history=[],profitRate=25,arazmanDeductionRate=14,digiFees=FEES,theme='روشن و مینیمال').items():self.data.setdefault(k,copy.deepcopy(v))
  self.page=0;self.mode='monitor';self.pending=False
  for p in self.data['active']+self.data['deleted']:self.baselines(p)
  central=QWidget();self.setCentralWidget(central);self.layout=QVBoxLayout(central)
  nav=QHBoxLayout();nav.setSpacing(12);self.logo=AnimatedLogo(self);self.logo.clicked.connect(lambda:self.section('monitor'));nav.addWidget(self.logo);nav.addStretch()
  for title,fn in [('کالای اصلاح نشده',self.filter_pending),('سطل آشغال',self.trash),('تنظیمات',self.settings)]:
   b=self.button(nav,title,fn);b.setObjectName('navButton');b.setCursor(Qt.PointingHandCursor)
  self.layout.addLayout(nav);bar=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('جستجو بین کالاها');self.search.setMinimumHeight(44);self.search.textChanged.connect(self.search_changed);bar.addWidget(self.search)
  for title,fn,name in [('افزودن کالا',self.add,'addButton'),('ویرایش کالا',self.edit,'editButton'),('حذف کالا',self.remove,'deleteButton')]:
   b=self.button(bar,title,fn);b.setObjectName(name);b.setFixedSize(124,44);b.setCursor(Qt.PointingHandCursor)
  self.layout.addLayout(bar);self.table=QTableWidget(0,16);self.table.setHorizontalHeaderLabels(HEAD[:4]+[fa(self.data['profitRate'])+'٪']+HEAD[5:]);self.table.setEditTriggers(QTableWidget.NoEditTriggers);self.table.setSelectionMode(QTableWidget.NoSelection);self.table.setFocusPolicy(Qt.NoFocus);self.table.setMouseTracking(False);self.platform_header=PlatformHeader(self.table);self.table.setHorizontalHeader(self.platform_header);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.table.verticalHeader().hide();self.table.setWordWrap(True);self.layout.addWidget(self.table)
  bottom=QHBoxLayout();sale_area=QWidget();sale_area.setFixedWidth(220);sale_layout=QHBoxLayout(sale_area);sale_layout.setContentsMargins(0,0,0,0);self.sale_button=self.button(sale_layout,'＋  ثبت فروش',self.sell);self.sale_button.setObjectName('saleButton');self.sale_button.setFixedSize(210,56);self.sale_button.setCursor(Qt.PointingHandCursor);bottom.addWidget(sale_area);bottom.addStretch();pager=QWidget();pager_layout=QHBoxLayout(pager);pager_layout.setContentsMargins(0,0,0,0);self.button(pager_layout,'قبلی',lambda:self.turn(-1));self.page_label=QLabel();self.page_label.setAlignment(Qt.AlignCenter);self.page_label.setMinimumWidth(70);pager_layout.addWidget(self.page_label);self.button(pager_layout,'بعدی',lambda:self.turn(1));bottom.addWidget(pager);bottom.addStretch();balance=QWidget();balance.setFixedWidth(220);version_layout=QHBoxLayout(balance);version_layout.setContentsMargins(0,0,0,0);version_label=QLabel('V'+VERSION);version_label.setLayoutDirection(Qt.LeftToRight);version_label.setAlignment(Qt.AlignLeft|Qt.AlignVCenter);version_layout.addWidget(version_label);bottom.addWidget(balance);self.layout.addLayout(bottom)
  self.apply_theme();self.render();self.timer=QTimer(self);self.timer.timeout.connect(self.render);self.timer.start(60000)
 def button(self,layout,title,fn):
  b=QPushButton(title);b.clicked.connect(fn);layout.addWidget(b);return b
 def persist(self):
  tmp=FILE.with_suffix('.tmp');tmp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf8');os.replace(tmp,FILE)
 def history(self,p,label,before,after):self.data['history'].append(dict(productId=p['id'],label=label,before=before,after=after,date=today()))
 def record_stock_event(self,p,typ,before,**extra):self.data['stockEvents'].append(dict(productId=p['id'],type=typ,before=before,after=p['stock'],change=p['stock']-before,date=today(),**extra))
 def target(self,p):return p['purchasePrice']+rounded(p['purchasePrice']*p.get('profitRateOverride',self.data['profitRate'])/100)
 def price(self,p,c):
  if p.get('purchasePrice') is None:return None
  if c=='digikala':return None if p.get('commission') is None else solve(self.target(p),p['commission'],p.get('platformRate',0) if p.get('digiMode')=='credit' else 0,self.data['digiFees'])
  if c=='arazman':return math.ceil(self.target(p)*100/(100-self.data['arazmanDeductionRate']))
  if c=='inperson' or c in SOCIAL and p.get('publishedChannels',{}).get(c):return self.target(p)
  return p.get(c+'Price')
 def baselines(self,p):
  p.setdefault('confirmedPrices',{})
  for c in ['arazman']+SOCIAL:
   v=self.price(p,c)
   if v is not None:p['confirmedPrices'].setdefault(c,v)
 def pending_price(self,p,c):
  v=self.price(p,c);old=p.get('digiConfirmedPrice') if c=='digikala' else p.get('confirmedPrices',{}).get(c)
  return v is not None and old is not None and v!=old
 def section(self,s):self.mode=s;self.pending=False;self.page=0;self.render()
 def search_changed(self):self.page=0;self.render()
 def filter_pending(self):self.mode='monitor';self.pending=not self.pending;self.page=0;self.render()
 def turn(self,d):self.page=max(0,self.page+d);self.render()
 def render(self):
  entries=self.data['deleted'] if self.mode=='deleted' else self.data['active'];entries=[(i+1,p) for i,p in enumerate(entries) if matches(p['name'],self.search.text()) and (not self.pending or any(self.pending_price(p,channel) for channel in CHANNELS))];pages=max(1,math.ceil(len(entries)/10));self.page=min(self.page,pages-1);self.page_label.setText(fa(f'{self.page+1} / {pages}'));entries=entries[self.page*10:self.page*10+10];self.table.setRowCount(len(entries));self.table.setHorizontalHeaderLabels(HEAD[:4]+[fa(self.data['profitRate'])+'٪']+HEAD[5:])
  for r,(n,p) in enumerate(entries):
   self.table.setRowHeight(r,66)
   for col,v in enumerate([fa(n),p['name'],money(p.get('purchasePrice')),fa(p.get('stock',0)),money(self.target(p))+'\n'+money(self.target(p)-p['purchasePrice'])]):self.cell(r,col,v)
   for col,c in enumerate(CHANNELS,start=5):
    v=self.price(p,c)
    if c in SOCIAL and not p.get('publishedChannels',{}).get(c):self.cellbutton(r,col,'ثبت انتشار',lambda checked=False,p=p,c=c:self.publish(p,c))
    elif c=='digikala' and p.get('commission') is None:self.cellbutton(r,col,'کمیسیون وارد نشده',lambda checked=False,p=p:self.commission(p))
    elif self.pending_price(p,c):self.cellbutton(r,col,money(v)+' ✓',lambda checked=False,p=p,c=c:self.confirm_price(p,c),True)
    else:self.cell(r,col,money(v))
   days=max(1,(date.today()-date.fromisoformat(p.get('firstPurchaseDate',today()))).days+1);self.cell(r,14,fa(days)+' روز' if p['stock'] else 'ناموجود','#16844a' if p['stock'] else '#d23a50')
   self.cellbutton(r,15,'برگرداندن کالا' if self.mode=='deleted' else 'مشاهده',lambda checked=False,p=p:self.restore(p) if self.mode=='deleted' else self.report(p))
 def cell(self,r,c,text,color=None):
  self.table.removeCellWidget(r,c);item=QTableWidgetItem(text);item.setTextAlignment(Qt.AlignCenter);item.setToolTip(text)
  if color:item.setForeground(QColor(color))
  self.table.setItem(r,c,item)
 def cellbutton(self,r,c,text,fn,purple=False):
  b=QPushButton(text);b.clicked.connect(fn)
  if purple:b.setObjectName('pendingPrice');b.setProperty('glowColor','#a269d7')
  self.table.setCellWidget(r,c,b)
 def dialog(self,title):
  d=ThemedDialog(self,title);return d,d.content_layout
 def form(self,title,fields,purchase_date=False):
  d,l=self.dialog(title);f=QFormLayout();l.addLayout(f);controls={}
  for key,label,value,kind in fields:
   w=QLineEdit(str(value)) if kind=='text' else QDoubleSpinBox() if kind=='percent' else QSpinBox()
   if kind!='text':w.setRange(0,1000 if kind=='percent' else 2000000000);w.setValue(value);w.setGroupSeparatorShown(True);w.setButtonSymbols(QAbstractSpinBox.NoButtons)
   f.addRow(label,w);controls[key]=w
  purchase={'value':today()}
  if purchase_date:
   date_row=QHBoxLayout();l.addLayout(date_row);date_label=QLabel('تاریخ خرید: '+fa(jd(today())));date_row.addWidget(date_label);today_button=QPushButton('تاریخ امروز');date_row.addWidget(today_button)
   d.setFixedSize(640,740);calendar=PersianCalendar(d);calendar.setWindowFlags(Qt.Widget);l.addWidget(calendar);calendar.show()
   def set_date(value):purchase['value']=value;date_label.setText('تاریخ خرید: '+fa(jd(value)))
   def pick_date(value):
    selected=value.togregorian().isoformat()
    set_date(selected)
   calendar.choose=pick_date
   def reset_today():
    set_date(today());calendar.anchor=jdatetime.date.today().replace(day=1);calendar.draw()
   today_button.clicked.connect(reset_today)
  buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('تأیید');buttons.button(QDialogButtonBox.Cancel).setText('لغو');buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject);l.addWidget(buttons)
  if d.exec()!=QDialog.Accepted:return None
  result={k:(w.text().strip() if isinstance(w,QLineEdit) else w.value()) for k,w in controls.items()}
  if purchase_date:result['purchaseDate']=purchase['value']
  return result
 def choose(self):
  d,l=self.dialog('انتخاب کالا با نام یا شماره');search,listing=self.product_picker(l);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('تأیید');buttons.button(QDialogButtonBox.Cancel).setText('لغو');buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject);l.addWidget(buttons)
  if d.exec()!=QDialog.Accepted:return None
  item=listing.currentItem();p=next((p for p in self.data['active'] if item and item.checkState()==Qt.Checked and p['id']==item.data(Qt.UserRole)),None)
  return p
 def product_picker(self,layout):
  group=QWidget();group.setObjectName('productSearchGroup');section=QVBoxLayout(group);section.setContentsMargins(12,12,12,12);section.setSpacing(8);search=QLineEdit();search.setPlaceholderText('نام یا شماره کالا');listing=QListWidget();listing.setMaximumHeight(130);listing.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);section.addWidget(search);section.addWidget(listing);layout.addWidget(group)
  def refresh():
   listing.clear();query=search.text().strip()
   listing.setVisible(bool(query))
   if not query:return
   for index,product in enumerate(self.data['active'],1):
    if (num(query).isdigit() and index==int(num(query))) or (not num(query).isdigit() and matches(product['name'],query)):
     item=QListWidgetItem(fa(index)+' — '+product['name']);item.setData(Qt.UserRole,product['id']);item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Unchecked);listing.addItem(item)
  def tick(item):
   listing.blockSignals(True)
   if item.checkState()==Qt.Checked:
    for index in range(listing.count()):
     other=listing.item(index)
     if other is not item:other.setCheckState(Qt.Unchecked)
    listing.setCurrentItem(item)
   else:listing.setCurrentRow(-1)
   listing.blockSignals(False);listing.currentItemChanged.emit(listing.currentItem(),None)
  listing.itemChanged.connect(tick);search.textChanged.connect(refresh);refresh();return search,listing
 def yes(self,title,text):
  d,l=self.dialog(title);message=QLabel(text);message.setWordWrap(True);l.addWidget(message);buttons=QDialogButtonBox();yes=buttons.addButton('بله',QDialogButtonBox.AcceptRole);no=buttons.addButton('خیر',QDialogButtonBox.RejectRole);buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject);l.addWidget(buttons);return d.exec()==QDialog.Accepted
 def add(self):
  v=self.form('افزودن کالا',[('name','نام کالا','','text'),('stock','موجودی',0,'int'),('purchasePrice','قیمت خرید (تومان)',0,'int'),('commission','کمیسیون اختیاری (%)','','text')],purchase_date=True)
  if not v:return
  if not v['name']:QMessageBox.warning(self,'خطا','نام کالا الزامی است.');return
  try:commission=None if not v['commission'] else float(num(v['commission']));assert commission is None or 0<=commission<=100
  except (ValueError,AssertionError):QMessageBox.warning(self,'خطا','کمیسیون معتبر نیست.');return
  purchase=v['purchaseDate']
  p=dict(id=str(uuid.uuid4()),name=v['name'],stock=v['stock'],purchasePrice=v['purchasePrice'],firstPurchaseDate=purchase)
  if commission is not None:p.update(commission=commission,digiMode='cash');p['digiConfirmedPrice']=self.price(p,'digikala')
  self.baselines(p);self.data['active'].append(p);self.record_stock_event(p,'initial',0,purchasePrice=p['purchasePrice']);self.persist();self.render()
 def remove(self):
  p=self.choose()
  if p and self.yes('حذف کالا','کالا به سطل آشغال منتقل شود؟'):self.data['active'].remove(p);self.data['deleted'].append(p);self.persist();self.render()
 def restore(self,p):self.data['deleted'].remove(p);self.data['active'].append(p);self.persist();self.render()
 def edit(self):
  d,l=self.dialog('ویرایش کالا');d.setFixedWidth(860);search,listing=self.product_picker(l);tabs=QTabWidget();tabs.setUsesScrollButtons(False);l.addWidget(tabs);selected={'product':None};controls={};info=QLabel('کالا را از فهرست انتخاب کنید');l.addWidget(info)
  specifications=[('name','تغییر نام کالا',[('value','نام کالا','text')]),('purchasePrice','قیمت خرید',[('value','قیمت خرید (تومان)','int')]),('increase','افزایش موجودی',[('value','تعداد خرید جدید','int'),('cost','قیمت خرید هر واحد (تومان)','int')]),('stock','تغییر موجودی',[('value','موجودی','int')]),('profitRateOverride','سود اختصاصی',[('value','درصد سود','percent')]),('commission','کمیسیون',[('value','درصد کمیسیون','percent'),('platform','توسعه پلتفرم اعتباری (%)','percent')])]
  for key,label,fields in specifications:
   page=QWidget();form=QFormLayout(page);controls[key]={}
   for field,text,kind in fields:
    widget=QLineEdit() if kind=='text' else QDoubleSpinBox() if kind=='percent' else QSpinBox()
    if kind!='text':widget.setRange(0,100 if key=='commission' else 1000 if kind=='percent' else 2000000000);widget.setButtonSymbols(QAbstractSpinBox.NoButtons);widget.setGroupSeparatorShown(True)
    form.addRow(text,widget);controls[key][field]=widget
   if key=='profitRateOverride':default=QCheckBox('استفاده از سود پیش‌فرض');form.addRow(default)
   if key=='commission':credit=QCheckBox('تسویه اعتباری');form.addRow(credit)
   tabs.addTab(page,label)
  tabs.setEnabled(False);buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);save=buttons.button(QDialogButtonBox.Save);save.setText('ثبت تغییرات');save.setEnabled(False);buttons.button(QDialogButtonBox.Cancel).setText('لغو');buttons.rejected.connect(d.reject);l.addWidget(buttons)
  def selection():
   item=listing.currentItem();product=next((p for p in self.data['active'] if item and item.checkState()==Qt.Checked and p['id']==item.data(Qt.UserRole)),None);selected['product']=product;tabs.setEnabled(bool(product));save.setEnabled(bool(product))
   if not product:info.setText('کالا را از فهرست انتخاب کنید');return
   info.setText(product['name']+' — '+('موجود' if product['stock'] else 'ناموجود'))
   for key,_,_ in specifications:
    value=product['name'] if key=='name' else 1 if key=='increase' else product.get(key,self.data['profitRate'] if key=='profitRateOverride' else 0)
    widget=controls[key]['value'];widget.setText(value) if key=='name' else widget.setValue(value or 0)
   controls['increase']['cost'].setValue(product['purchasePrice']);controls['commission']['platform'].setValue(product.get('platformRate',0));default.setChecked('profitRateOverride' not in product);credit.setChecked(product.get('digiMode')=='credit');tabs.setTabVisible(5,product.get('commission') is not None)
  listing.currentItemChanged.connect(selection)
  def commit():
   product=selected['product']
   if not product:return
   key=specifications[tabs.currentIndex()][0];widget=controls[key]['value'];value=widget.text().strip() if key=='name' else widget.value();before=product['stock'];old=product.get(key)
   if key=='name' and not value:info.setText('نام کالا الزامی است');return
   if key=='increase':
    if not value:info.setText('تعداد خرید باید بیشتر از صفر باشد');return
    cost=controls[key]['cost'].value();product['purchasePrice']=rounded((before*product['purchasePrice']+value*cost)/(before+value));product['stock']+=value;self.record_stock_event(product,'increase',before,purchasePrice=cost,averagePurchasePrice=product['purchasePrice'])
   elif key=='profitRateOverride' and default.isChecked():product.pop(key,None);self.history(product,'بازگشت سود به پیش‌فرض',old,self.data['profitRate'])
   else:
    product[key]=value;self.history(product,key,old,value)
    if key=='stock':self.record_stock_event(product,'set',before)
    if key=='commission':product['platformRate']=controls[key]['platform'].value();product['digiMode']='credit' if credit.isChecked() else 'cash'
   self.persist();self.render();selection();info.setText(product['name']+' — تغییرات ثبت شد')
  buttons.accepted.connect(commit);d.exec()
 def edit_field(self,p,key,parent):
  if key=='commission':parent.accept();self.commission(p);return
  fields=[('value','مقدار جدید',p.get(key,0),'text' if key=='name' else 'percent' if key=='profitRateOverride' else 'int')]
  if key=='increase':fields=[('value','تعداد خرید جدید',1,'int'),('cost','قیمت خرید هر واحد جدید',p['purchasePrice'],'int')]
  if key=='profitRateOverride' and self.yes('درصد سود','می‌خواهید به سود پیش‌فرض برگردید؟'):
   old=p.pop(key,None);self.history(p,'بازگشت سود به پیش‌فرض',old,self.data['profitRate']);self.persist();parent.accept();self.render();return
  v=self.form('ویرایش کالا',fields)
  if not v:return
  old=p.get(key);before=p['stock']
  if key=='increase':
   if not v['value']:return
   p['purchasePrice']=rounded((before*p['purchasePrice']+v['value']*v['cost'])/(before+v['value']));p['stock']+=v['value'];self.record_stock_event(p,'increase',before,purchasePrice=v['cost'],averagePurchasePrice=p['purchasePrice'])
  else:
   if key=='name' and not v['value']:return
   p[key]=v['value'];self.history(p,key,old,p[key])
   if key=='stock':self.record_stock_event(p,'set',before)
  self.persist();parent.accept();self.render()
 def commission(self,p):
  v=self.form('کمیسیون دیجیکالا',[('commission','کمیسیون (%)',p.get('commission',0),'percent'),('platformRate','توسعه پلتفرم اعتباری (%)',p.get('platformRate',0),'percent')])
  if not v:return
  if v['commission']>100 or v['platformRate']>100:return
  old=p.get('commission');p.update(v);p['digiMode']='credit' if self.yes('نوع تسویه','محاسبه اعتباری باشد؟') else 'cash'
  if old is None:p['digiConfirmedPrice']=self.price(p,'digikala')
  self.history(p,'کمیسیون',old,p['commission']);self.persist();self.render()
 def publish(self,p,c):
  if self.yes('ثبت انتشار',f'آیا «{p["name"]}» را در {CHANNELS[c]} منتشر کرده‌اید؟'):
   p.setdefault('publishedChannels',{})[c]=True;p.setdefault('confirmedPrices',{})[c]=self.price(p,c);self.history(p,'انتشار '+CHANNELS[c],False,True);self.persist();self.render()
 def confirm_price(self,p,c):
  new=self.price(p,c);old=p.get('digiConfirmedPrice') if c=='digikala' else p['confirmedPrices'][c]
  if self.yes('تأیید اصلاح قیمت',f'قیمت قبلی: {money(old)}\nقیمت جدید: {money(new)}\nآیا در {CHANNELS[c]} اصلاح کرده‌اید؟'):
   if c=='digikala':p['digiConfirmedPrice']=new
   else:p['confirmedPrices'][c]=new
   self.history(p,'تأیید قیمت '+CHANNELS[c],old,new);self.persist();self.render()
 def trash(self):
  d=QDialog(self,Qt.Popup|Qt.FramelessWindowHint);self.trash_window=d;d.setObjectName('settingsWindow');d.setFixedSize(560,390);d.setLayoutDirection(Qt.RightToLeft)
  layout=QVBoxLayout(d);layout.setContentsMargins(1,1,1,12);layout.setSpacing(12)
  bar=QWidget();bar.setObjectName('settingsTitle');bar.setFixedHeight(48);row=QHBoxLayout(bar);row.setContentsMargins(16,8,12,8);title=QLabel('سطل آشغال');title.setObjectName('settingsTitleLabel');row.addWidget(title);row.addStretch();close=QPushButton('×');close.setObjectName('settingsClose');close.setFixedSize(34,32);close.clicked.connect(d.close);row.addWidget(close);layout.addWidget(bar)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame);layout.addWidget(scroll)
  def refresh():
   old=scroll.takeWidget()
   if old:old.deleteLater()
   content=QWidget();items=QVBoxLayout(content);items.setContentsMargins(14,4,14,4);items.setSpacing(10)
   if not self.data['deleted']:
    empty=QLabel('سطل آشغال خالی است');empty.setAlignment(Qt.AlignCenter);items.addWidget(empty)
   for product in self.data['deleted']:
    item=QWidget();line=QHBoxLayout(item);line.setContentsMargins(6,4,6,4);name=QLabel(product['name']);name.setWordWrap(True);line.addWidget(name,1);button=QPushButton('بازگشت به لیست فروش');button.setMinimumHeight(40);line.addWidget(button)
    def bring_back(checked=False,product=product):
     if product in self.data['deleted']:self.restore(product)
     refresh()
    button.clicked.connect(bring_back);items.addWidget(item)
   items.addStretch();scroll.setWidget(content)
  refresh();d.move(self.mapToGlobal(self.rect().center())-d.rect().center());d.show()
 def settings(self):
  d=QDialog(self,Qt.Popup|Qt.FramelessWindowHint);self.settings_window=d;d.setObjectName('settingsWindow');d.setFixedSize(860,470);d.setLayoutDirection(Qt.RightToLeft)
  l=QVBoxLayout(d);l.setContentsMargins(1,1,1,12);l.setSpacing(12)
  bar=QWidget();bar.setObjectName('settingsTitle');bar.setFixedHeight(48);row=QHBoxLayout(bar);row.setContentsMargins(16,8,12,8);title=QLabel('تنظیمات');title.setObjectName('settingsTitleLabel');row.addWidget(title);row.addStretch();close=QPushButton('×');close.setObjectName('settingsClose');close.setFixedSize(34,32);close.clicked.connect(d.close);row.addWidget(close);l.addWidget(bar)
  tabs=QTabWidget();tabs.setObjectName('settingsTabs');l.addWidget(tabs)
  notice=QLabel(d);notice.setObjectName('settingsNotice');notice.setAlignment(Qt.AlignCenter);notice.setAttribute(Qt.WA_TransparentForMouseEvents);notice.hide();notice_timer=QTimer(d);notice_timer.setSingleShot(True);notice_timer.timeout.connect(notice.hide);tabs.currentChanged.connect(lambda _:notice.hide())
  def notify(message):
   notice.setText(message);notice.adjustSize();notice.move((d.width()-notice.width())//2,bar.height()+tabs.tabBar().height()+24);notice.show();notice.raise_();notice_timer.start(2200)
  for label,key in [('سود پیش‌فرض','profitRate'),('آرازمان','arazmanDeductionRate')]:
   page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(24,20,24,20);form=QFormLayout();layout.addLayout(form);value=QDoubleSpinBox();value.setRange(0,99.99 if key=='arazmanDeductionRate' else 1000);value.setSuffix(' ٪');value.setValue(self.data[key]);form.addRow('درصد کسر از مبلغ فروش' if key=='arazmanDeductionRate' else 'درصد سود پیش‌فرض',value);layout.addStretch();save=QPushButton('ثبت تغییرات');layout.addWidget(save)
   def save_rate(checked=False,key=key,value=value):
    old=self.data[key];self.data[key]=value.value()
    if old!=value.value():
     for product in self.data['active']:self.history(product,key,old,value.value())
     self.persist();self.render()
    notify('درصد سود پیش‌فرض تغییر کرد' if key=='profitRate' else 'درصد آرازمان تغییر کرد')
   save.clicked.connect(save_rate);tabs.addTab(page,label)
  page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(24,12,24,12);form=QFormLayout();layout.addLayout(form);controls={}
  for key,label in zip(FEES,['درصد مجموع پردازش','کف مجموع هزینه (تومان)','سقف مجموع هزینه (تومان)','هزینه لیبل (تومان)','مالیات خدمات (%)']):
   value=QDoubleSpinBox() if 'percent' in key else QSpinBox();value.setRange(0,99 if 'percent' in key else 2000000000);value.setGroupSeparatorShown(True);value.setValue(self.data['digiFees'][key]);form.addRow(label,value);controls[key]=value
  save=QPushButton('ثبت تغییرات');layout.addWidget(save)
  def save_fees():
   values={key:control.value() for key,control in controls.items()}
   if values['processing_min']>values['processing_max']:notify('کف هزینه نباید بیشتر از سقف باشد');return
   self.data['digiFees']=values;self.persist();self.render();notify('تنظیمات دیجیکالا تغییر کرد')
  save.clicked.connect(save_fees);tabs.addTab(page,'دیجیکالا')
  for label in ['اسنپ شاپ','باسلام']:
   placeholder=QWidget();tabs.addTab(placeholder,label)
  page=QWidget();layout=QGridLayout(page);layout.setContentsMargins(24,24,24,24)
  for index,theme in enumerate(THEMES):
   button=QPushButton(theme);button.setMinimumHeight(68);button.setCheckable(True);button.setChecked(theme==self.data['theme']);layout.addWidget(button,index//2,index%2)
   def choose_theme(checked=False,theme=theme):
    self.data['theme']=theme;self.apply_theme();self.persist()
    for button in page.findChildren(QPushButton):button.setChecked(button.text()==theme)
    notify('تم برنامه اعمال شد')
   button.clicked.connect(choose_theme)
  tabs.addTab(page,'تم برنامه')
  tabs.addTab(build_update_tab(self,d,notify,ROOT),'آپدیت برنامه')
  for control in d.findChildren(QAbstractSpinBox):control.setButtonSymbols(QAbstractSpinBox.NoButtons)
  d.move(self.mapToGlobal(self.rect().center())-d.rect().center());d.show()
 def setting_rate(self,key):
  v=self.form('تغییر درصد',[('value','درصد',self.data[key],'percent')])
  if v and (key!='arazmanDeductionRate' or v['value']<100):
   old=self.data[key];self.data[key]=v['value']
   for p in self.data['active']:self.history(p,key,old,v['value'])
   self.persist();self.render()
 def setting_fees(self):
  labels=['درصد مجموع پردازش','کف مجموع هزینه','سقف مجموع هزینه','هزینه لیبل','مالیات خدمات (%)'];v=self.form('هزینه‌های دیجیکالا',[(k,label,self.data['digiFees'][k],'percent' if 'percent' in k else 'int') for k,label in zip(FEES,labels)])
  if v and v['processing_min']<=v['processing_max']:self.data['digiFees']=v;self.persist();self.render()
 def theme_dialog(self):
  d,l=self.dialog('تغییر تم')
  for theme in THEMES:self.button(l,theme,lambda checked=False,theme=theme:self.set_theme(theme,d))
  d.exec()
 def set_theme(self,theme,d):self.data['theme']=theme;self.apply_theme();self.persist();d.accept()
 def apply_theme(self):
  check_icon=(Path(__file__).resolve().parent/'icons'/'check.svg').as_posix()
  halo,halo_hover,purple={'روشن و مینیمال':('#f1e9fb','#e5d6f7','#8652b9'),'سرمه‌ای و مسی':('#30263f','#443255','#ce9cf5'),'تیره و نئونی':('#292039','#3d2b53','#ce9cf5'),'کرم و زیتونی':('#eee6f1','#e1d1eb','#8553a5')}.get(self.data['theme'],('#f1e9fb','#e5d6f7','#8652b9'))
  bg,surface,text,accent,border=THEMES.get(self.data['theme'],THEMES['روشن و مینیمال']);add,edit,danger,sale= {'روشن و مینیمال':('#377d91','#9274b1','#b97884','#235e75'),'سرمه‌ای و مسی':('#a8734f','#687e92','#986273','#d49a68'),'تیره و نئونی':('#148d91','#795bbb','#b05385','#07b5b3'),'کرم و زیتونی':('#78865a','#b28e58','#aa7567','#596947')}.get(self.data['theme'],('#377d91','#9274b1','#b97884','#235e75'));self.logo.accent=accent;self.platform_header.bg=accent;self.platform_header.viewport().update();self.table.setProperty('theme',self.data['theme']);self.sale_button.setProperty('glowColor',accent);QApplication.instance().setProperty('accentColor',accent);QApplication.instance().setStyleSheet(f'''QComboBox::drop-down{{border:0;width:24px;background:transparent;}} QComboBox::down-arrow{{image:none;}} QScrollBar:vertical{{background:{surface};width:10px;margin:3px;border:0;}} QScrollBar::handle:vertical{{background:{accent};min-height:28px;border-radius:5px;}} QScrollBar::handle:vertical:hover{{background:{QColor(accent).lighter(125).name()};}} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}} QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:transparent;}} QListView::indicator,QCheckBox::indicator{{width:18px;height:18px;border:2px solid {accent};border-radius:4px;background:{surface};}} QListView::indicator:checked,QCheckBox::indicator:checked{{background:{accent};image:url("{check_icon}");}} QListView::item{{padding:7px;border-bottom:1px solid {border};}} QListView::item:selected{{background:{bg};color:{text};}} QDialog#settingsWindow{{border:1px solid {border};}} QWidget#productSearchGroup{{border:1px solid {border};border-radius:10px;background:{surface};}} QWidget#settingsTitle,QLabel#settingsTitleLabel{{background:{accent};color:white;font-size:16px;font-weight:bold;}} QPushButton#settingsClose{{background:transparent;color:white;border:0;font-size:23px;padding:0;}} QPushButton#settingsClose:hover{{background:{QColor(accent).lighter(130).name()};}} QTabWidget#settingsTabs::pane{{border:0;padding:12px;}} QTabWidget#settingsTabs QTabBar::tab{{border-radius:12px;margin:4px 3px;padding:11px 13px;font-weight:bold;}} QTabWidget#settingsTabs QTabBar::tab:selected{{background:{accent};color:white;border-color:{accent};}} QTabWidget#settingsTabs QTabBar::tab:hover{{background:{QColor(accent).lighter(120).name()};color:white;}} QLabel#settingsNotice{{background:{accent};color:white;border-radius:10px;padding:12px 24px;font-size:13px;}} QTabBar::tab{{background:{surface};color:{text};padding:10px 16px;border:1px solid {border};}} QTabBar::tab:selected{{background:{accent};color:white;}} QTabBar::tab:hover{{background:{QColor(accent).lighter(120).name()};color:white;}} QPushButton:checked{{border:2px solid {accent};color:{accent};}} QWidget{{background:{bg};color:{text};font-family:Vazirmatn;font-size:12px;}} QDialog,QTableWidget,QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTextEdit{{background:{surface};}} QPushButton{{background:{surface};border:1px solid {border};border-radius:8px;padding:9px;color:{text};}} QPushButton:hover{{border-color:{accent};color:{accent};}} QHeaderView::section{{background:{accent};color:white;padding:9px;border:0;}} QTableWidget{{gridline-color:{border};border:1px solid {border};}} QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox{{padding:8px;border:1px solid {border};border-radius:6px;}} QPushButton:hover{{background:{accent};color:white;border:1px solid {accent};}} QPushButton#navButton{{background:{surface};color:{accent};border:1px solid {border};font-size:11px;padding:7px 12px;}} QPushButton#navButton:hover{{background:{accent};color:white;border-color:{accent};}} QPushButton#addButton,QPushButton#editButton,QPushButton#deleteButton{{font-size:13px;font-weight:bold;border-radius:9px;}} QPushButton#addButton{{background:{add};color:white;}} QPushButton#addButton:hover{{background:{QColor(add).darker(125).name()};border:2px solid {QColor(add).lighter(145).name()};}} QPushButton#editButton{{background:{edit};color:white;}} QPushButton#editButton:hover{{background:{QColor(edit).darker(130).name()};border:2px solid {QColor(edit).lighter(155).name()};}} QPushButton#deleteButton{{background:{danger};color:white;border-color:{danger};}} QPushButton#deleteButton:hover{{background:{QColor(danger).darker(140).name()};border:2px solid {QColor(danger).lighter(160).name()};}} QPushButton#saleButton{{background:{sale};color:white;font-size:18px;font-weight:bold;border-radius:10px;border:1px solid {QColor(sale).lighter(125).name()};border-bottom:5px solid {QColor(sale).darker(150).name()};padding:8px 20px;}} QPushButton#saleButton:hover{{background:{QColor(sale).lighter(120).name()};color:white;border:1px solid {QColor(sale).lighter(165).name()};border-bottom:5px solid {QColor(sale).darker(145).name()};}} QPushButton#saleButton:pressed{{border-bottom:1px solid {sale};padding-top:12px;}} QPushButton#pendingPrice{{background:qradialgradient(cx:0.5,cy:0.5,radius:0.8,fx:0.5,fy:0.5,stop:0 {halo},stop:1 {surface});color:{purple};border:1px solid {halo};border-radius:7px;}} QPushButton#pendingPrice:hover{{background:{halo_hover};color:{purple};border:1px solid {purple};}} QTableWidget::item:hover{{background:transparent;}} QTableWidget::item:focus{{outline:none;}}''')
 def sale_form(self,p,sale=None):
  d,l=self.dialog('ویرایش فروش' if sale else 'ثبت فروش');l.addWidget(QLabel('تاریخ: '+fa(jd(sale['date'] if sale else today()))));f=QFormLayout();l.addLayout(f);q=QSpinBox();q.setButtonSymbols(QAbstractSpinBox.NoButtons);q.setRange(1,max(1,p['stock']+(sale['quantity'] if sale else 0)));q.setValue(sale['quantity'] if sale else 1);c=QComboBox()
  for key,label in CHANNELS.items():
   if self.price(p,key) is not None or sale and sale['channel']==key:c.addItem(label,key)
  if sale:c.setCurrentIndex(c.findData(sale['channel']))
  price=QLineEdit(str(sale['unitPrice']) if sale else '');price.setPlaceholderText('اختیاری؛ قیمت جدول');summary=QLabel();f.addRow('تعداد',q);f.addRow('نحوه فروش',c);f.addRow('قیمت هر واحد (تومان)',price);l.addWidget(summary)
  def refresh():summary.setText('قیمت پیش‌فرض: '+money(self.price(p,c.currentData()))+' | موجودی: '+fa(p['stock']))
  c.currentIndexChanged.connect(refresh);refresh();buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.button(QDialogButtonBox.Ok).setText('تأیید');buttons.button(QDialogButtonBox.Cancel).setText('لغو');buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject);l.addWidget(buttons)
  if d.exec()!=QDialog.Accepted:return
  try:unit=int(num(price.text())) if price.text().strip() else self.price(p,c.currentData());assert unit is not None and unit>=0;assert q.value()<=p['stock']+(sale['quantity'] if sale else 0)
  except (ValueError,AssertionError):QMessageBox.warning(self,'خطا','قیمت یا تعداد معتبر نیست.');return
  before=p['stock']
  if sale and c.currentData()=='digikala' and sale.get('feeSnapshot',{}).get('commission') is None:
   QMessageBox.warning(self,'خطا','کمیسیون زمان فروش ثبت نشده است.');return
  if sale:
   self.history(p,'ویرایش فروش',copy.deepcopy(sale),dict(quantity=q.value(),unitPrice=unit,channel=c.currentData()));p['stock']+=sale['quantity']-q.value();sale.update(quantity=q.value(),unitPrice=unit,totalPrice=unit*q.value(),channel=c.currentData(),manualPrice=True);self.record_stock_event(p,'editSale',before)
  else:
   sale=dict(id=str(uuid.uuid4()),productId=p['id'],productName=p['name'],date=today(),quantity=q.value(),channel=c.currentData(),unitPrice=unit,totalPrice=unit*q.value(),manualPrice=bool(price.text()),purchasePriceAtSale=p['purchasePrice'],feeSnapshot=dict(commission=p.get('commission'),platform=p.get('platformRate',0) if p.get('digiMode')=='credit' else 0,digi=copy.deepcopy(self.data['digiFees']),arazmanRate=self.data['arazmanDeductionRate']));self.data['sales'].append(sale);p['stock']-=q.value();self.record_stock_event(p,'sale',before)
  self.persist();self.render()
 def sale_notice(self,message):
  if hasattr(self,'sale_toast'):self.sale_toast.hide();self.sale_toast.deleteLater()
  toast=QLabel(message,self);self.sale_toast=toast;toast.setAttribute(Qt.WA_TransparentForMouseEvents);toast.setStyleSheet('background:#17864b;color:white;border:1px solid #40b879;border-radius:12px;padding:14px 24px;font-size:14px;font-weight:bold;');toast.adjustSize();toast.move((self.width()-toast.width())//2,self.height()-toast.height()-85);effect=QGraphicsOpacityEffect(toast);toast.setGraphicsEffect(effect);effect.setOpacity(1);toast.show();toast.raise_();animation=QPropertyAnimation(effect,b'opacity',toast);self.sale_toast_animation=animation;animation.setDuration(650);animation.setStartValue(1.0);animation.setEndValue(0.0);animation.finished.connect(toast.hide);delay=QTimer(toast);delay.setSingleShot(True);delay.timeout.connect(animation.start);delay.start(3000)
 def sell(self):
  d,l=self.dialog('ثبت فروش');d.setFixedWidth(680);l.addWidget(QLabel('تاریخ: '+fa(jd(today()))));search,listing=self.product_picker(l);selected={'product':None};form=QFormLayout();l.addLayout(form);quantity=QSpinBox();quantity.setRange(1,1);quantity.setButtonSymbols(QAbstractSpinBox.NoButtons);quantity.setGroupSeparatorShown(True);form.addRow('تعداد فروش',quantity)
  channels=QWidget();grid=QGridLayout(channels);grid.setContentsMargins(0,0,0,0);group=QButtonGroup(d);group.setExclusive(True);channel_buttons={}
  for index,(key,label) in enumerate(CHANNELS.items()):
   button=QPushButton(label);button.setCheckable(True);button.setVisible(False);group.addButton(button);channel_buttons[key]=button;grid.addWidget(button,index//3,index%3)
  form.addRow('نحوه فروش',channels);price=QLineEdit();price.setPlaceholderText('اختیاری؛ قیمت پیش‌فرض جدول');form.addRow('قیمت هر واحد (تومان)',price);summary=QLabel('کالا را جستجو و تیک انتخاب را بزنید');summary.setWordWrap(True);l.addWidget(summary);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);confirm=buttons.button(QDialogButtonBox.Ok);confirm.setText('ثبت فروش');confirm.setEnabled(False);buttons.button(QDialogButtonBox.Cancel).setText('لغو');buttons.rejected.connect(d.reject);l.addWidget(buttons)
  def current_channel():return next((key for key,button in channel_buttons.items() if button.isChecked() and button.isVisible()),None)
  def refresh_summary():
   product=selected['product'];channel=current_channel();confirm.setEnabled(bool(product and product['stock']>0 and channel))
   if not product:summary.setText('کالا را جستجو و تیک انتخاب را بزنید');return
   if not product['stock']:summary.setText('این کالا ناموجود است');return
   if not channel:summary.setText('برای این کالا هنوز قیمت فروش پلتفرمی ثبت نشده است');return
   unit=self.price(product,channel)
   try:unit=int(num(price.text())) if price.text().strip() else unit
   except ValueError:summary.setText('قیمت واردشده معتبر نیست');confirm.setEnabled(False);return
   summary.setText('موجودی: '+fa(product['stock'])+' | قیمت هر واحد: '+money(unit)+' | جمع فروش: '+money(unit*quantity.value()))
  def choose_product():
   item=listing.currentItem();product=next((p for p in self.data['active'] if item and item.checkState()==Qt.Checked and p['id']==item.data(Qt.UserRole)),None);selected['product']=product;quantity.setRange(1,max(1,product['stock']) if product else 1);quantity.setValue(1);price.clear();group.setExclusive(False)
   for key,button in channel_buttons.items():button.setChecked(False);button.setVisible(bool(product and self.price(product,key) is not None))
   group.setExclusive(True)
   first=next((button for button in channel_buttons.values() if not button.isHidden()),None)
   if first:first.setChecked(True)
   refresh_summary()
  listing.currentItemChanged.connect(choose_product);group.buttonClicked.connect(refresh_summary);quantity.valueChanged.connect(refresh_summary);price.textChanged.connect(refresh_summary)
  def commit():
   product=selected['product'];channel=current_channel()
   try:
    assert product and channel;count=quantity.value();assert 0<count<=product['stock'];unit=int(num(price.text())) if price.text().strip() else self.price(product,channel);assert unit is not None and unit>=0
   except (ValueError,AssertionError):summary.setText('کالا، قیمت یا تعداد فروش معتبر نیست');return
   sale=dict(id=str(uuid.uuid4()),productId=product['id'],productName=product['name'],date=today(),quantity=count,channel=channel,unitPrice=unit,totalPrice=unit*count,manualPrice=bool(price.text().strip()),purchasePriceAtSale=product['purchasePrice'],feeSnapshot=dict(commission=product.get('commission'),platform=product.get('platformRate',0) if product.get('digiMode')=='credit' else 0,digi=copy.deepcopy(self.data['digiFees']),arazmanRate=self.data['arazmanDeductionRate']))
   before=product['stock'];product['stock']-=count;self.data['sales'].append(sale);self.record_stock_event(product,'sale',before);self.persist();self.render();d.accept();self.sale_notice(fa(count)+' عدد «'+product['name']+'» فروخته شد')
  buttons.accepted.connect(commit);d.exec()
 def profit(self,s):
  if not s.get('feeSnapshot') or s.get('purchasePriceAtSale') is None:return None
  f=s['feeSnapshot'];v=s['unitPrice']
  if s['channel']=='digikala':v=net(v,f['commission'],f['platform'],f['digi'])
  elif s['channel']=='arazman':v*=1-f['arazmanRate']/100
  elif s['channel'] in ['basalam','snappshop']:return None
  return rounded((v-s['purchasePriceAtSale'])*s['quantity'])
 def report(self,p):
  d,l=self.dialog('گزارش '+p['name']);d.resize(1120,650);tabs=QTabWidget();tabs.setObjectName('settingsTabs');l.addWidget(tabs);sales=[s for s in self.data['sales'] if s['productId']==p['id']];active=[s for s in sales if not s.get('cancelled')]
  def text_tab(title,text):w=QTextEdit();w.setReadOnly(True);w.setPlainText(text);tabs.addTab(w,title)
  profits=[self.profit(s) for s in active];summary=QWidget();cards=QGridLayout(summary);cards.setContentsMargins(18,18,18,18);cards.setSpacing(14)
  values=[('تاریخ اولین خرید',fa(jd(p['firstPurchaseDate']))),('مجموع قیمت خرید',money(sum(s['purchasePriceAtSale']*s['quantity'] for s in active if s.get('purchasePriceAtSale') is not None))),('قیمت خرید فعلی',money(p['purchasePrice'])),('درصد سود فعلی',fa(p.get('profitRateOverride',self.data['profitRate']))+'٪'),('تعداد کل فروخته‌شده',fa(sum(s['quantity'] for s in active))+' عدد'),('مجموع مبلغ فروش',money(sum(s['totalPrice'] for s in active))),('مجموع سود فروش‌ها',money(sum(v for v in profits if v is not None))),('تعداد ثبت‌های فروش',fa(len(active)))]
  for index,(label,value) in enumerate(values):
   card=QWidget();card.setObjectName('productSearchGroup');layout=QVBoxLayout(card);layout.setContentsMargins(18,14,18,14);caption=QLabel(label);caption.setAlignment(Qt.AlignCenter);number=QLabel(value);number.setAlignment(Qt.AlignCenter);number.setStyleSheet('font-size:18px;font-weight:bold;');layout.addWidget(caption);layout.addWidget(number);cards.addWidget(card,index//4,index%4)
   if label=='مجموع سود فروش‌ها':
    dark=self.data['theme'] in ['سرمه‌ای و مسی','تیره و نئونی'];green_bg,green_border,green_text=('#183b31','#33735b','#a0efbe') if dark else ('#e9f8ee','#a8dcb8','#247642');card.setStyleSheet(f'QWidget#productSearchGroup{{background:{green_bg};border:1px solid {green_border};border-radius:10px;}} QLabel{{background:transparent;border:0;color:{green_text};}}')
  note=QLabel('هر ثبت فروش با قیمت خرید و قیمت فروش همان زمان، جداگانه در تاریخچه ثبت شده است.');note.setWordWrap(True);cards.addWidget(note,2,0,1,4)
  unknown=sum(v is None for v in profits)
  if unknown:cards.addWidget(QLabel(fa(unknown)+' ثبت فروش فاقد اطلاعات کافی برای محاسبه سود است و در مجموع سود لحاظ نشده.'),3,0,1,4)
  tabs.addTab(summary,'خلاصه کالا')
  box=QWidget();bl=QVBoxLayout(box);st=QTableWidget(len(sales),10);st.setHorizontalHeaderLabels(['','تاریخ','روش فروش','تعداد','خرید هر واحد','فروش هر واحد','جمع فروش','سود هر واحد','سود کل','وضعیت']);st.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);st.verticalHeader().hide();st.setEditTriggers(QTableWidget.NoEditTriggers);st.setSelectionMode(QTableWidget.NoSelection);st.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed);st.setColumnWidth(0,38);st.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
  chosen={'row':None};checks=[]
  def pick_order(row,checked):
   chosen['row']=row if checked else None
   if checked:
    for index,check in enumerate(checks):
     if index!=row:check.blockSignals(True);check.setChecked(False);check.blockSignals(False)
  for r,s in enumerate(sales):
   holder=QWidget();check_layout=QHBoxLayout(holder);check_layout.setContentsMargins(0,0,0,0);check_layout.setAlignment(Qt.AlignCenter);check=QCheckBox();checks.append(check);check.toggled.connect(lambda checked,row=r:pick_order(row,checked));check_layout.addWidget(check);st.setCellWidget(r,0,holder)
   if s.get('cancelled'):holder.setStyleSheet('background:'+('#41272c' if self.data['theme'] in ['سرمه‌ای و مسی','تیره و نئونی'] else '#fff0f1')+';')
   profit=self.profit(s);unit_profit=None if profit is None else rounded(profit/s['quantity'])
   for c,v in enumerate([fa(jd(s['date'])),CHANNELS[s['channel']],fa(s['quantity']),money(s.get('purchasePriceAtSale')),money(s['unitPrice']),money(s['totalPrice']),money(unit_profit),money(profit),'لغوشده' if s.get('cancelled') else 'قیمت دستی' if s.get('manualPrice') else 'ثبت‌شده']):
    item=QTableWidgetItem(v);item.setTextAlignment(Qt.AlignCenter)
    if s.get('cancelled'):item.setBackground(QColor('#41272c' if self.data['theme'] in ['سرمه‌ای و مسی','تیره و نئونی'] else '#fff0f1'))
    st.setItem(r,c+1,item)
   st.setRowHeight(r,46)
  bl.addWidget(st);actions=QHBoxLayout();bl.addLayout(actions)
  def selected_sale():return sales[chosen['row']] if chosen['row'] is not None else None
  def edit_sale():
   s=selected_sale()
   if s and not s.get('cancelled'):d.accept();self.sale_form(p,s);self.report(p)
  def cancel_sale():
   s=selected_sale()
   if s and not s.get('cancelled') and self.yes('لغو فروش','تعداد فروخته‌شده به موجودی برگردد؟'):
    before=p['stock'];p['stock']+=s['quantity'];s['cancelled']=True;self.record_stock_event(p,'cancelSale',before);self.history(p,'لغو فروش',s['totalPrice'],None);self.persist();self.render();d.accept();self.report(p)
  self.button(actions,'ویرایش فروش انتخاب‌شده',edit_sale);self.button(actions,'لغو فروش انتخاب‌شده',cancel_sale);tabs.addTab(box,'تاریخچه فروش')
  def history_table(title,headers,rows):
   table=QTableWidget(len(rows),len(headers));table.setHorizontalHeaderLabels(headers);table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);table.verticalHeader().hide();table.setEditTriggers(QTableWidget.NoEditTriggers);table.setSelectionMode(QTableWidget.NoSelection);table.setWordWrap(True)
   for row,values in enumerate(rows):
    for column,value in enumerate(values):
     item=QTableWidgetItem(str(value));item.setTextAlignment(Qt.AlignCenter);table.setItem(row,column,item)
   table.resizeRowsToContents();tabs.addTab(table,title)
  events=[e for e in self.data['stockEvents'] if e['productId']==p['id']];names=dict(initial='موجودی اولیه',increase='خرید جدید',set='تغییر موجودی',sale='فروش',editSale='ویرایش فروش',cancelSale='لغو فروش')
  history_table('موجودی و خرید',['تاریخ','رویداد','موجودی قبل','تغییر تعداد','موجودی بعد','خرید هر واحد','میانگین خرید'],[[fa(jd(e['date'])),names.get(e['type'],e['type']),fa(e['before']),fa(e['change']),fa(e['after']),money(e.get('purchasePrice')),money(e.get('averagePurchasePrice'))] for e in reversed(events)])
  labels={'name':'نام کالا','purchasePrice':'قیمت خرید','stock':'موجودی','commission':'کمیسیون','profitRateOverride':'سود اختصاصی','profitRate':'سود پیش‌فرض','arazmanDeductionRate':'درصد آرازمان','unitPrice':'قیمت واحد','quantity':'تعداد','channel':'روش فروش','totalPrice':'جمع فروش'}
  def display(value,key=''):
   if value is None:return '—'
   if isinstance(value,dict):return '\n'.join(labels.get(k,k)+': '+display(v,k) for k,v in value.items() if k in labels)
   if isinstance(value,bool):return 'بله' if value else 'خیر'
   if key in ['purchasePrice','unitPrice','totalPrice']:return money(value)
   if key=='channel':return CHANNELS.get(value,value)
   return fa(value)
  history_table('تاریخچه تغییرات',['تاریخ','نوع تغییر','مقدار قبلی','مقدار جدید'],[[fa(jd(e['date'])),labels.get(e['label'],e['label']),display(e.get('before'),e['label']),display(e.get('after'),e['label'])] for e in reversed(self.data['history']) if e['productId']==p['id']]);d.exec()
 def quit_after_update(self):QApplication.instance().quit()
 def closeEvent(self,event):
  if not self.yes('خروج','همه تغییرات ذخیره شوند و پشتیبان گرفته شود؟'):event.ignore();return
  try:self.persist();backup=ROOT/'backups';backup.mkdir(exist_ok=True);(backup/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')).write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf8')
  except OSError as ex:QMessageBox.critical(self,'ذخیره‌سازی',str(ex));event.ignore();return
  event.accept()
if __name__=='__main__':
 if sys.platform=='win32':
  import ctypes
  ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Arazman.Desktop')
 app=QApplication(sys.argv);app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent/'icons'/'arazman-app.ico')));font_path=Path(__file__).resolve().parent/'fonts'/'Vazirmatn-Regular.ttf';font_id=QFontDatabase.addApplicationFont(str(font_path));app.setFont(QFont('Vazirmatn',10));hover=NeonHover(app);app.installEventFilter(hover);app.setLayoutDirection(Qt.RightToLeft);window=App();window.showMaximized();sys.exit(app.exec())
