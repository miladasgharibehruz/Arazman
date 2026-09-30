"""GitHub release checks and data backups for Arazman."""
import json, re, shutil, uuid
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
VERSION='1.1'
ASSET='Arazman-Setup.exe'
def latest_release(repo):
 if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('مخزن اختصاصی آرازمان هنوز تنظیم نشده است.')
 req=Request(f'https://api.github.com/repos/{repo}/releases/latest',headers={'User-Agent':'Arazman-Updater','Accept':'application/vnd.github+json'})
 with urlopen(req,timeout=20) as response:release=json.load(response)
 assets=release.get('assets',[]);asset=next((a for a in assets if a['name']==ASSET),None)
 if not asset:raise ValueError('فایل نصب آرازمان در آخرین انتشار پیدا نشد.')
 checksum_asset=next((a for a in assets if a['name']==ASSET+'.sha256'),None)
 if not checksum_asset:raise ValueError('فایل بررسی صحت دانلود در انتشار وجود ندارد.')
 with urlopen(Request(checksum_asset['browser_download_url'],headers={'User-Agent':'Arazman-Updater'}),timeout=20) as response:checksum=response.read(4096).decode('ascii').split()[0]
 if not re.fullmatch('[a-fA-F0-9]{64}',checksum):raise ValueError('فایل بررسی صحت معتبر نیست.')
 return dict(version=release['tag_name'].lstrip('vV'),url=asset['browser_download_url'],sha256=checksum,notes=release.get('body',''))
def newer(a,b=VERSION):
 def parts(v):return tuple((list(map(int,re.findall(r'\d+',v)))+[0]*4)[:4])
 return parts(a)>parts(b)
def snapshot(root,data):
 folder=Path(root)/'backups';folder.mkdir(exist_ok=True)
 target=folder/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json');target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');return target

def read_backup(path):
 data=json.loads(Path(path).read_text(encoding='utf8'))
 if not isinstance(data,dict) or not all(isinstance(data.get(k),list) for k in ['active','deleted','sales','stockEvents','history']):raise ValueError('ساختار فایل پشتیبان معتبر نیست.')
 ids=set()
 for p in data['active']+data['deleted']:
  if not isinstance(p,dict) or not isinstance(p.get('id'),str) or p['id'] in ids or not isinstance(p.get('name'),str) or not isinstance(p.get('stock'),int) or p['stock']<0:raise ValueError('اطلاعات کالا در پشتیبان معتبر نیست.')
  ids.add(p['id'])
 return data

def build_update_tab(app,dialog,notify,root):
 import os,sys,subprocess,threading
 from PySide6.QtCore import QTimer
 from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QMessageBox
 root=Path(root);install=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
 config=install/'update_config.json'
 try:repo=json.loads(config.read_text(encoding='utf8')).get('repo','')
 except (OSError,ValueError):repo=''
 page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(24,12,24,12)
 status=QLabel('نسخه فعلی: '+VERSION);status.setWordWrap(True);layout.addWidget(status)
 row=QHBoxLayout();layout.addLayout(row);check=QPushButton('بررسی آپدیت');apply=QPushButton('نصب نسخه جدید');apply.setEnabled(False);row.addWidget(check);row.addWidget(apply)
 entries=QListWidget();layout.addWidget(entries);actions=QHBoxLayout();layout.addLayout(actions)
 def refresh():
  entries.clear();folder=root/'backups';folder.mkdir(exist_ok=True)
  for path in sorted(folder.glob('*.json'),reverse=True):entries.addItem(path.name)
 def backup():
  try:app.persist();snapshot(root,app.data);refresh();notify('پشتیبان اطلاعات ساخته شد')
  except Exception as error:notify('خطا در پشتیبان‌گیری: '+str(error))
 def selected():
  item=entries.currentItem()
  return root/'backups'/item.text() if item else None
 def restore():
  path=selected()
  if not path:notify('یک پشتیبان انتخاب کنید');return
  if QMessageBox.question(dialog,'بازیابی اطلاعات','اطلاعات فعلی با این پشتیبان جایگزین شود؟ پیش از بازیابی، پشتیبان ایمنی ساخته می‌شود.')!=QMessageBox.Yes:return
  try:
   data=read_backup(path);snapshot(root,app.data);old=app.data;app.data=data
   try:app.persist()
   except Exception:app.data=old;raise
   app.apply_theme();app.render();refresh();notify('اطلاعات بازیابی شد')
  except Exception as error:notify('بازیابی انجام نشد: '+str(error))
 def delete():
  path=selected()
  if not path:return
  if QMessageBox.question(dialog,'حذف پشتیبان','پشتیبان انتخاب‌شده حذف شود؟')==QMessageBox.Yes:
   try:path.unlink();refresh();notify('پشتیبان حذف شد')
   except OSError as error:notify(str(error))
 def folder():
  if os.name=='nt':os.startfile(str(root/'backups'))
 for text,fn in [('بکاپ جدید',backup),('بازیابی',restore),('حذف بکاپ',delete),('پوشه بکاپ',folder)]:
  button=QPushButton(text);button.clicked.connect(fn);actions.addWidget(button)
 result={};release={};timer=QTimer(page)
 def poll():
  if 'done' not in result:return
  timer.stop();check.setEnabled(True)
  if result.get('error'):status.setText('بررسی انجام نشد: '+result['error']);return
  release.clear();release.update(result['release'])
  if newer(release['version']):
   status.setText('نسخه جدید: '+release['version']);apply.setEnabled(bool(getattr(sys,'frozen',False)))
   if not getattr(sys,'frozen',False):status.setText(status.text()+' — نصب خودکار در نسخه نصبی ویندوز فعال می‌شود.')
  else:status.setText('برنامه به‌روز است')
 def worker():
  try:result['release']=latest_release(repo)
  except Exception as error:result['error']=str(error)
  finally:result['done']=True
 def check_release():
  if not repo:notify('مخزن اختصاصی آرازمان هنوز تعیین نشده است');return
  result.clear();check.setEnabled(False);apply.setEnabled(False);status.setText('در حال بررسی نسخه جدید…');threading.Thread(target=worker,daemon=True).start();timer.start(100)
 timer.timeout.connect(poll);check.clicked.connect(check_release)
 def launch(mode,extra):
  updater=install/'Arazman Updater.exe'
  if not updater.exists():notify('فایل آپدیت‌کننده در بسته نصبی پیدا نشد');return
  app.persist();snapshot(root,app.data);copy=root/'Updater';copy.mkdir(exist_ok=True);target=copy/updater.name;shutil.copy2(updater,target)
  args=[str(target),'--'+mode,'--pid',str(os.getpid()),'--install-dir',str(install),'--data-dir',str(root),'--current-version',VERSION]+extra
  subprocess.Popen(args,cwd=str(copy));dialog.close();QTimer.singleShot(0,app.quit_after_update)
 def install_release():
  if QMessageBox.question(dialog,'نصب آپدیت','نسخه جدید نصب شود؟ برنامه بسته می‌شود و قبل از نصب پشتیبان گرفته خواهد شد.')==QMessageBox.Yes:
   try:launch('update',['--url',release['url'],'--version',release['version'],'--sha256',release['sha256']])
   except Exception as error:notify('آپدیت آغاز نشد: '+str(error))
 apply.clicked.connect(install_release)
 rollback=QPushButton('بازگشت به نسخه قبلی برنامه');layout.addWidget(rollback)
 def rollback_previous():
  versions=root/'versions';backups=sorted((p for p in versions.glob('*') if p.is_dir() and (p/'app').is_dir()),reverse=True)
  if not backups:notify('پشتیبان نسخه قبلی برنامه موجود نیست');return
  if QMessageBox.question(dialog,'بازگشت نسخه','نسخه قبلی برنامه برگردانده شود؟ اطلاعات فروش فعلی حفظ می‌شود.')==QMessageBox.Yes:
   try:launch('rollback',['--backup',str(backups[0])])
   except Exception as error:notify(str(error))
 rollback.clicked.connect(rollback_previous);rollback.setEnabled(bool(getattr(sys,'frozen',False)));refresh();return page
