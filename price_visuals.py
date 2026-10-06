"""Native, animated price surfaces and readable settlement breakdowns."""
import math
from PySide6.QtCore import Qt,QTimer,QRectF,Signal,QEvent
from PySide6.QtGui import QPainter,QColor,QPen,QFont,QLinearGradient
from PySide6.QtWidgets import QWidget,QPushButton,QLabel,QVBoxLayout,QHBoxLayout,QFrame,QScrollArea,QButtonGroup,QSizePolicy

class PriceSurface(QPushButton):
 def __init__(self,text,theme,themes,pending=False):
  super().__init__(text);self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.pending=pending;self.surface=QColor(themes[theme][1]);self.ink=QColor('#cfabf2' if self.surface.lightness()<128 else '#8052af') if pending else QColor(themes[theme][2]);self.accent=QColor('#956ac2') if pending else QColor(themes[theme][3]);self.hover=0.;self.target=0.;self.setCursor(Qt.PointingHandCursor);self.setAutoDefault(False);self.setProperty('glowColor',self.accent.name());self.timer=QTimer(self);self.timer.setInterval(16);self.timer.timeout.connect(self.advance)
 def advance(self):
  self.hover+=(self.target-self.hover)*.24
  if abs(self.target-self.hover)<.01:self.hover=self.target;self.timer.stop()
  self.update()
 def enterEvent(self,event):self.target=1.;self.timer.start();super().enterEvent(event)
 def leaveEvent(self,event):self.target=0.;self.timer.start();super().leaveEvent(event)
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=QRectF(self.hover*2,self.hover*2,self.width()-self.hover*4,self.height()-self.hover*4);base=QColor(self.surface);tint=QColor(self.accent);tint.setAlpha(int((32 if self.pending else 0)+self.hover*24));p.setPen(Qt.NoPen);shadow=QColor(0,0,0,int(self.hover*30));p.setBrush(shadow);p.drawRoundedRect(r.translated(0,2),8,8);p.setBrush(base);p.drawRoundedRect(r,8,8);p.setBrush(tint);p.drawRoundedRect(r,8,8)
  light=QColor(255,255,255,int(self.hover*30));p.setPen(QPen(light,1));p.drawLine(r.topLeft().toPoint()+__import__('PySide6.QtCore',fromlist=['QPoint']).QPoint(8,0),r.topRight().toPoint()-__import__('PySide6.QtCore',fromlist=['QPoint']).QPoint(8,0));p.setPen(self.ink);amount=self.text().replace(' تومان','');font=QFont(self.font());font.setBold(True);font.setPixelSize(12)
  while font.pixelSize()>9 and __import__('PySide6.QtGui',fromlist=['QFontMetrics']).QFontMetrics(font).horizontalAdvance(amount)>r.width()-6:font.setPixelSize(font.pixelSize()-1)
  p.setFont(font);p.drawText(r.adjusted(2,2,-2,-r.height()*.3),Qt.AlignCenter,amount);font.setBold(False);font.setPixelSize(9);p.setFont(font);p.drawText(r.adjusted(2,r.height()*.5,-2,-1),Qt.AlignCenter,'تومان');p.end()

class AnimatedDonut(QWidget):
 hovered=Signal(int)
 def __init__(self,parts,total,money,colors,text):
  super().__init__();self.parts=parts;self.total=total;self.money=money;self.colors=colors;self.ink=text;self.progress=0.;self.active=-1;self.setMinimumSize(290,290);self.setMouseTracking(True);self.clock=QTimer(self);self.clock.setInterval(16);self.clock.timeout.connect(self.step);self.clock.start();self.setAccessibleName('نمودار ترکیب قیمت فروش')
 def step(self):
  self.progress=min(1,self.progress+.035);self.update()
  if self.progress==1:self.clock.stop()
 def geometry_ring(self):
  diameter=min(self.width(),self.height())-44;return QRectF((self.width()-diameter)/2,(self.height()-diameter)/2,diameter,diameter)
 def highlight(self,index):
  if self.active!=index:self.active=index;self.hovered.emit(index);self.update()
 def mouseMoveEvent(self,event):
  r=self.geometry_ring();dx=event.position().x()-r.center().x();dy=event.position().y()-r.center().y();radius=math.hypot(dx,dy);angle=(math.degrees(math.atan2(dx,-dy))+360)%360;total=sum(max(0,v) for _,v,_ in self.parts);start=0;found=-1
  if r.width()/2-42<=radius<=r.width()/2+7:
   for i,(_,value,_) in enumerate(self.parts):
    end=start+max(0,value)/max(total,1)*360
    if start<=angle<end and value>0:found=i;break
    start=end
  self.highlight(found)
 def leaveEvent(self,event):self.highlight(-1);super().leaveEvent(event)
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=self.geometry_ring();ring=r.adjusted(18,18,-18,-18);track=QColor(self.ink);track.setAlpha(15);p.setPen(QPen(track,30));p.drawEllipse(ring);total=sum(max(0,v) for _,v,_ in self.parts);start=90.;ease=1-(1-self.progress)**3
  for i,(_,value,_) in enumerate(self.parts):
   span=max(0,value)/max(total,1)*360
   if span<=0:continue
   color=QColor(self.colors[i]);rect=ring.adjusted(-3,-3,3,3) if self.active==i else ring;pen=QPen(color.lighter(115) if self.active==i else color,34 if self.active==i else 30);pen.setCapStyle(Qt.FlatCap);p.setPen(pen);gap=min(1.8,span*.18);p.drawArc(rect,round((start-gap/2)*16),-round(max(0,span-gap)*ease*16));start-=span
  title=self.parts[self.active][0] if self.active>=0 else 'قیمت فروش';value=self.parts[self.active][1] if self.active>=0 else self.total*ease;p.setPen(QColor(self.ink));font=QFont(self.font());font.setPixelSize(12);p.setFont(font);p.drawText(r.adjusted(35,85,-35,-120),Qt.AlignCenter|Qt.TextWordWrap,title);font.setPixelSize(17);font.setBold(True);p.setFont(font);p.drawText(r.adjusted(34,120,-34,-75),Qt.AlignCenter|Qt.TextWordWrap,self.money(value));p.end()

class DetailRow(QFrame):
 def __init__(self,chart,index,title,amount,percent,color):
  super().__init__();self.chart=chart;self.index=index;self.setObjectName('detailRow');self.setMouseTracking(True);l=QHBoxLayout(self);l.setContentsMargins(12,9,12,9);l.setSpacing(10);dot=QLabel('●');dot.setStyleSheet('color:'+color+';font-size:15px;background:transparent;');l.addWidget(dot);label=QLabel(title);label.setTextFormat(Qt.PlainText);l.addWidget(label,1);number=QLabel(amount);number.setStyleSheet('font-weight:700;background:transparent;');l.addWidget(number);share=QLabel(percent);share.setFixedWidth(58);share.setAlignment(Qt.AlignCenter);share.setStyleSheet('color:'+color+';background:transparent;font-weight:600;');l.addWidget(share)
 def enterEvent(self,event):self.chart.highlight(self.index);super().enterEvent(event)
 def leaveEvent(self,event):self.chart.highlight(-1);super().leaveEvent(event)

def show_details(app,api,product,channel):
 if channel not in ['digikala','arazman','basalam']:return
 from inventory_ui import breakdown
 d,l=app.dialog('جزئیات قیمت '+api['CHANNELS'][channel]);d.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint);d.resize(1050,min(820,d.screen().availableGeometry().height()-40));bg,surface,ink,accent,border=api['THEMES'][app.data['theme']];dark=QColor(surface).lightness()<128
 d.setStyleSheet('QFrame#detailCard{background:'+surface+';border:1px solid '+border+';border-radius:14px;} QFrame#detailRow{background:'+surface+';border:0;border-radius:9px;} QFrame#detailRow:hover{background:'+bg+';} QLabel{background:transparent;}')
 top=QHBoxLayout();l.addLayout(top);identity=QLabel(product['name']);identity.setTextFormat(Qt.PlainText);identity.setStyleSheet('font-size:17px;font-weight:700;');top.addWidget(identity,1);mode={'value':'credit' if channel=='arazman' else 'cash'};group=QButtonGroup(d);group.setExclusive(True)
 for key,title in [('cash','نقدی'),('credit','اعتباری')]:
  button=QPushButton(title);button.setCheckable(True);button.setChecked(mode['value']==key);button.setVisible(channel!='basalam');group.addButton(button);top.addWidget(button)
  def choose(checked=False,key=key):mode['value']=key;refresh()
  button.clicked.connect(choose)
 hero=QFrame();hero.setObjectName('detailCard');hl=QHBoxLayout(hero);hl.setContentsMargins(22,16,22,16);hl.addWidget(QLabel('قیمت نهایی فروش'),1);price_label=QLabel();price_label.setStyleSheet('font-size:27px;font-weight:800;color:'+accent+';');hl.addWidget(price_label);l.addWidget(hero)
 cards=QHBoxLayout();l.addLayout(cards);values=[]
 for caption,color in [('قیمت خرید','#6a9cdf'),('مجموع کسورات','#c696e7'),('سود','#67c397')]:
  card=QFrame();card.setObjectName('detailCard');cl=QVBoxLayout(card);cl.setContentsMargins(18,12,18,12);cl.addWidget(QLabel(caption));value=QLabel();value.setStyleSheet('font-size:20px;font-weight:700;color:'+ (color if dark else QColor(color).darker(150).name())+';');cl.addWidget(value);cards.addWidget(card,1);values.append(value)
 body=QWidget();bl=QHBoxLayout(body);bl.setContentsMargins(0,0,0,0);bl.setSpacing(20);l.addWidget(body,1);explanation=QLabel();explanation.setWordWrap(True);explanation.setStyleSheet('padding:12px 16px;border:1px solid '+border+';border-radius:10px;font-size:12px;');l.addWidget(explanation)
 def refresh():
  while bl.count():
   old=bl.takeAt(0).widget();old.hide();old.deleteLater()
  total,parts=breakdown(app,api,product,channel,mode['value']);price_label.setText(api['money'](total));deductions=sum(v for _,v,_ in parts[1:-1])
  for label,value in zip(values,[parts[0][1],deductions,parts[-1][1]]):label.setText(api['money'](value))
  palette=['#6a9cdf','#b68bdb','#e1a65c','#58b8c4','#3f909c','#d0bd65','#d88796','#67c397']
  colors=[palette[i%len(palette)] if dark else QColor(palette[i%len(palette)]).darker(115).name() for i in range(len(parts))];chart=AnimatedDonut(parts,total,api['money'],colors,ink);bl.addWidget(chart,4)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame);rows=QWidget();rl=QVBoxLayout(rows);rl.setContentsMargins(0,0,0,0);rl.setSpacing(5);head=QHBoxLayout();head.addWidget(QLabel('جزئیات هزینه و درآمد'),1);head.addWidget(QLabel('مبلغ / سهم از فروش'));rl.addLayout(head)
  for i,(title,value,_) in enumerate(parts):rl.addWidget(DetailRow(chart,i,title,api['money'](value),api['fa'](round(value/max(total,1)*100,1))+'٪',colors[i]))
  rl.addStretch();scroll.setWidget(rows);bl.addWidget(scroll,6)
  if channel=='digikala':
   import inventory_engine as E
   cfg=E.fees(app.data,product);source=lambda key:'اختصاصی' if key in product.get('digiFeeOverride',{}) else 'عمومی';explanation.setText('پردازش: '+api['fa'](cfg['processing_percent'])+'٪ ('+source('processing_percent')+')    •    کف: '+api['money'](cfg['processing_min'])+' ('+source('processing_min')+')    •    سقف: '+api['money'](cfg['processing_max'])+' ('+source('processing_max')+')\nمالیات خدمات '+api['fa'](cfg['tax_percent'])+'٪ بر کمیسیون، اضافه اعتباری، لیبل و نیمه مشمول مالیات پردازش محاسبه می‌شود.')
  elif channel=='arazman':explanation.setText('اعتباری: کسر ۶٫۶٪ از قیمت فروش. در فروش نقدی این کسر انجام نمی‌شود؛ مبلغ قیمت جدول برای هر دو روش یکسان است.')
  else:explanation.setText('باسلام: فقط کمیسیون اختصاصی این کالا از مبلغ فروش کسر می‌شود.')
  if parts[-1][1]<0:explanation.setText(explanation.text()+'\nسود این حالت منفی است؛ نمودار فقط سهم‌های مثبت را نشان می‌دهد.')
 refresh();d.exec()
