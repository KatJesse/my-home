"""Readable PDF exports and restorable ZIP snapshots for Mein Zuhause."""
import os, io, json, zipfile, sqlite3, shutil, tempfile, threading, time, html, re, calendar
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from bs4 import BeautifulSoup

TZ=ZoneInfo('Europe/Berlin')
LOCK=threading.RLock()
PDF_SECTIONS={
 'Notizen':['categories','notes','attachments','revisions'],
 'Vorräte':['pantry_items','pantry_categories','pantry_locations','pantry_shelves'],
 'Einkaufszettel':['shopping','shopping_archives','shopping_archive_items'],
 'Lager':['storage_boxes','storage_places'],
 'Plotten':['plot_orders','plot_stock','plot_purchases','plot_purchase_items','plot_foil_stock','plot_movements','plot_schema_migrations'],
 'Aufgaben':['task_lists','task_items'],
 'Essen':['food_recipes','food_ingredients','food_plan'],
 'Einstellungen':['app_settings'],
}
EXCLUDE={'users','sessions','note_search','hidden_categories'}
SENSITIVE={'nas_password','password','token','secret','api_key'}

def install_backup(app,db,require,safe_post,render,go,BASE,FILES,DB,cfg,smb_action):
 root=BASE/'sicherungen'; root.mkdir(parents=True,exist_ok=True)
 def admin(req):
  u=require(req)
  if u['role']!='admin':raise HTTPException(403,'Nur Administratoren')
  return u
 def stamp():return datetime.now(TZ).strftime('%Y-%m-%d_%H-%M-%S')
 def state():
  p=root/'status.json'
  try:return json.loads(p.read_text(encoding='utf-8'))
  except Exception:return {}
 def setstate(**kwargs):
  data=state();data.update(kwargs);(root/'status.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 def local_nas_path():
  # Home Assistant share mount, configured PDF destination, never /config as NAS substitute.
  configured=cfg().get('pdf_directory','/share/mein-zuhause-pdf')
  if configured==str(BASE/'pdf'):configured='/share/mein-zuhause-pdf'
  target=Path(configured).resolve()
  if not str(target).startswith('/share/') and target!=Path('/share'):
   raise RuntimeError('PDF-Verzeichnis muss im eingebundenen /share liegen, damit es als NAS-Ziel genutzt werden kann')
  target.mkdir(parents=True,exist_ok=True)
  return target/'MeinZuhause-Sicherungen'
 def publish(path,category,name):
  from app.main import remote_settings
  if remote_settings().get('nas_mode')=='smb':smb_action('put','MeinZuhause-Sicherungen/'+category,name,path)
  else:
   dest=local_nas_path()/category;dest.mkdir(parents=True,exist_ok=True)
   tmp=dest/(name+'.tmp');shutil.copy2(path,tmp);tmp.replace(dest/name)
 def pdf_font():
  for font in ('/usr/share/fonts/ttf/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
   if Path(font).exists():
    if 'HausUnicode' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('HausUnicode',font))
    return 'HausUnicode'
  return 'Helvetica'
 def build_pdf(section,path):
  font=pdf_font(); styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='HausCell',fontName=font,fontSize=7,leading=10,spaceAfter=3,wordWrap='CJK'))
  styles.add(ParagraphStyle(name='HausHead',fontName=font,fontSize=14,leading=19,spaceAfter=10))
  styles.add(ParagraphStyle(name='HausSub',fontName=font,fontSize=10,leading=14,spaceBefore=12,spaceAfter=6))
  def para(x):
   if x is None:return Paragraph('–',styles['HausCell'])
   if isinstance(x,bytes):return Paragraph('[Binärdaten]',styles['HausCell'])
   s=str(x)
   if '<' in s and '>' in s:s=BeautifulSoup(s,'html.parser').get_text(' ',strip=True)
   s=s[:4000]
   return Paragraph(html.escape(s).replace('\n','<br/>'),styles['HausCell'])
  story=[Paragraph(section+' – Mein Zuhause',styles['HausHead']),para('Export: '+datetime.now(TZ).strftime('%d.%m.%Y %H:%M')+' · alle gespeicherten Datensätze, einschließlich Archiv')]
  with db() as c:
   tables={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' AND name NOT LIKE 'note_search%' ")}
   # assign each table exactly once; include future tables in a separate PDF
   assigned={t for group in PDF_SECTIONS.values() for t in group}
   names=[t for t in PDF_SECTIONS.get(section,[]) if t in tables]
   if section=='Weitere Daten':names=sorted(tables-assigned-EXCLUDE)
   for table in names:
    story.append(Paragraph(table.replace('_',' ').title(),styles['HausSub']))
    cols=[r['name'] for r in c.execute('PRAGMA table_info("'+table+'")') if r['name'] not in SENSITIVE and not any(k in r['name'].lower() for k in ('password','secret','token'))]
    if section=='Einstellungen':
     rows=c.execute('SELECT * FROM app_settings WHERE key NOT LIKE ? AND key NOT LIKE ? AND key NOT LIKE ?',('%password%','%secret%','%token%')).fetchall()
    else:rows=c.execute('SELECT * FROM "'+table+'"').fetchall()
    if not rows:story.append(para('Keine Einträge'));continue
    # record-wise layout keeps every field readable on narrow A4 pages
    for n,r in enumerate(rows,1):
     data=[[para(col.replace('_',' ').title()),para(r[col])] for col in cols]
     tab=LongTable(data,colWidths=[39*mm,145*mm],repeatRows=0,hAlign='LEFT')
     tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eef2f6')),('LINEBELOW',(0,-1),(-1,-1),0.5,colors.HexColor('#d1d9e2')),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
     story.append(para('Datensatz '+str(n)));story.append(tab);story.append(Spacer(1,7))
  path.parent.mkdir(parents=True,exist_ok=True)
  SimpleDocTemplate(str(path),pagesize=A4,leftMargin=12*mm,rightMargin=12*mm,topMargin=15*mm,bottomMargin=15*mm).build(story)
 def make_zip(path):
  with LOCK:
   path.parent.mkdir(parents=True,exist_ok=True)
   fd,tmp=tempfile.mkstemp(dir=str(path.parent),suffix='.tmp');os.close(fd)
   try:
    with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
     z.writestr('manifest.json',json.dumps({'format':'mein-zuhause-backup-v1','created':datetime.now(TZ).isoformat()},ensure_ascii=False))
     with tempfile.TemporaryDirectory(dir=str(root)) as d:
      snapshot=Path(d)/'house.db'
      with db() as src,sqlite3.connect(snapshot) as dst:src.backup(dst)
      z.write(snapshot,'database/house.db')
     for f in FILES.rglob('*'):
      if f.is_file() and not f.is_symlink():z.write(f,'uploads/'+f.relative_to(FILES).as_posix())
    os.replace(tmp,path)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 def run_saving(monthly=False):
  with LOCK:
   try:
    timestamp=stamp();folder=root/'aktuell';folder.mkdir(parents=True,exist_ok=True)
    pdfs=[]
    for section in [*PDF_SECTIONS,'Weitere Daten']:
     pdf=folder/(section+'.pdf');build_pdf(section,pdf);publish(pdf,'PDFs/Aktuell',pdf.name);pdfs.append(pdf)
    zpath=folder/('MeinZuhause-'+timestamp+'.zip');make_zip(zpath)
    daily_name='MeinZuhause-'+datetime.now(TZ).strftime('%Y-%m-%d')+'.zip'
    publish(zpath,'Backup/Aktuell',daily_name)
    from app.main import remote_settings
    for age in range(7,10):
     expired='MeinZuhause-'+(datetime.now(TZ)-timedelta(days=age)).strftime('%Y-%m-%d')+'.zip'
     try:
      if remote_settings().get('nas_mode')=='smb':smb_action('del','MeinZuhause-Sicherungen/Backup/Aktuell',expired)
      else:(local_nas_path()/'Backup/Aktuell'/expired).unlink(missing_ok=True)
     except Exception:pass
    archives=sorted(folder.glob('MeinZuhause-*.zip'),reverse=True)
    for old in archives[7:]:old.unlink(missing_ok=True)
    # Daily NAS names are stable and old daily snapshots are pruned
    # monthly snapshots created only once per month, immutable after creation.
    if monthly:
     month=datetime.now(TZ).strftime('%Y-%m');monthdir=root/'monate'/month
     if not (monthdir/'MeinZuhause.zip').exists():
      monthdir.mkdir(parents=True,exist_ok=True)
      shutil.copy2(zpath,monthdir/'MeinZuhause.zip');publish(monthdir/'MeinZuhause.zip','Backup/Monatsarchive/'+month,'MeinZuhause.zip')
      for pdf in pdfs:
       shutil.copy2(pdf,monthdir/pdf.name);publish(monthdir/pdf.name,'PDFs/Monatsarchive/'+month,pdf.name)
    setstate(last_success=datetime.now(TZ).isoformat(),last_error='')
    return zpath
   except Exception as exc:
    setstate(last_error=datetime.now(TZ).isoformat()+': '+str(exc))
    raise
 def restore_zip(path):
  with LOCK:
   with zipfile.ZipFile(path) as z:
    names=z.namelist()
    if len(names)>10000 or sum(i.file_size for i in z.infolist())>2*1024**3:raise ValueError('Backup zu groß')
    if 'manifest.json' not in names or 'database/house.db' not in names:raise ValueError('Kein gültiges Mein-Zuhause-Backup')
    manifest=json.loads(z.read('manifest.json'))
    if manifest.get('format')!='mein-zuhause-backup-v1':raise ValueError('Unbekanntes Backupformat')
    for name in names:
     parts=Path(name).parts
     if name.startswith('/') or '..' in parts or '\\' in name or not (name in ('manifest.json','database/house.db') or name.startswith('uploads/')):raise ValueError('Ungültiger Dateipfad im Backup')
    with tempfile.TemporaryDirectory(dir=str(root)) as temp:
     d=Path(temp);z.extractall(d)
     restored=d/'database/house.db'
     with sqlite3.connect(restored) as check:
      if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Datenbank beschädigt')
      if not check.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='notes'").fetchone():raise ValueError('Datenbank nicht kompatibel')
     # preserve current state before replacing; require free disk space
     rescue=root/('vor-wiederherstellung-'+stamp()+'.zip');make_zip(rescue)
     with db() as c:
      c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
     shutil.copy2(restored,DB.with_suffix('.restore'))
     os.replace(DB.with_suffix('.restore'),DB)
     for suffix in ('-wal','-shm'):
      Path(str(DB)+suffix).unlink(missing_ok=True)
     incoming=d/'uploads'
     if incoming.exists():
      previous=root/('uploads-vor-wiederherstellung-'+stamp());FILES.rename(previous)
      shutil.copytree(incoming,FILES)
     else:
      previous=root/('uploads-vor-wiederherstellung-'+stamp());FILES.rename(previous);FILES.mkdir()
     setstate(last_restore=datetime.now(TZ).isoformat(),last_restore_rescue=str(rescue.name))
 def files_list():
  return [{'name':p.name,'size':p.stat().st_size,'modified':datetime.fromtimestamp(p.stat().st_mtime,TZ).strftime('%d.%m.%Y %H:%M')} for p in sorted((root/'aktuell').glob('MeinZuhause-*.zip'),reverse=True)]
 @app.get('/settings/backup',response_class=HTMLResponse)
 def backup_page(req:Request):
  admin(req)
  return render(req,'backup.html',status=state(),backups=files_list(),monthly=sorted((root/'monate').glob('*/MeinZuhause.zip'),reverse=True))
 @app.post('/settings/backup/create')
 def create(req:Request):
  admin(req);safe_post(req)
  try:run_saving(monthly=False)
  except Exception as exc:raise HTTPException(503,'Sicherung fehlgeschlagen: '+str(exc))
  return go('/settings/backup')
 @app.get('/settings/backup/download/{filename}')
 def download(req:Request,filename:str):
  admin(req)
  if not re.fullmatch(r'MeinZuhause-[0-9_-]+\.zip',filename):raise HTTPException(400)
  file=root/'aktuell'/filename
  if not file.exists():raise HTTPException(404)
  return FileResponse(file,filename=filename,media_type='application/zip')
 @app.post('/settings/backup/restore')
 async def restore(req:Request,upload:UploadFile=File(None),filename:str=Form(''),confirmation:str=Form('')):
  admin(req);safe_post(req)
  if confirmation!='WIEDERHERSTELLEN':raise HTTPException(400,'Bestätigung fehlt')
  with tempfile.NamedTemporaryFile(dir=str(root),suffix='.zip',delete=False) as tmp:
   target=Path(tmp.name)
   try:
    if upload and upload.filename:
     size=0
     while chunk:=await upload.read(1024*1024):
      size+=len(chunk)
      if size>2*1024**3:raise ValueError('Datei zu groß')
      tmp.write(chunk)
    else:
     if not re.fullmatch(r'MeinZuhause-[0-9_-]+\.zip',filename):raise ValueError('Backup auswählen')
     src=root/'aktuell'/filename
     if not src.exists():raise ValueError('Backup nicht vorhanden')
     shutil.copyfileobj(src.open('rb'),tmp)
   except Exception:
    target.unlink(missing_ok=True);raise
  try:restore_zip(target)
  except Exception as exc:raise HTTPException(400,'Wiederherstellung fehlgeschlagen: '+str(exc))
  finally:target.unlink(missing_ok=True)
  return go('/settings/backup?restored=1')
 def schedule():
  # run at 02:00 local Europe/Berlin, catch up after downtime (once per calendar day)
  while True:
   try:
    local=datetime.now(TZ)
    if local.hour>=2:
     key=local.strftime('%Y-%m-%d')
     st=state()
     if st.get('last_auto_day')!=key:
      # monthly snapshot of previous month on first day, plus current month if absent
      monthly=False
      try:run_saving(monthly=monthly)
      except Exception as exc:print('Mein Zuhause Backup:',str(exc),flush=True)
      setstate(last_auto_day=key)
    # Freeze the month on its final calendar day at 23:59.
    if local.day==calendar.monthrange(local.year,local.month)[1] and local.hour==23 and local.minute==59:
     monthkey=local.strftime('%Y-%m')
     if state().get('last_monthly')!=monthkey:
      try:run_saving(monthly=True);setstate(last_monthly=monthkey)
      except Exception as exc:print('Mein Zuhause Monatsarchiv:',str(exc),flush=True)
   except Exception as exc:print('Mein Zuhause Backup scheduler:',str(exc),flush=True)
   time.sleep(60)
 @app.on_event('startup')
 def start_backup_scheduler():
  if not getattr(app.state,'backup_scheduler_started',False):
   app.state.backup_scheduler_started=True
   threading.Thread(target=schedule,daemon=True,name='mein-zuhause-backup').start()
