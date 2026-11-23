"""Vehicle and trailer records, services, documents and printable reports."""
from datetime import date
from pathlib import Path
from uuid import uuid4
import html, re
from fastapi import Request,Form,File,UploadFile,HTTPException
from fastapi.responses import HTMLResponse,FileResponse
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def install_kfz(app,db,require,writer,safe_post,render,go,now,BASE):
 root=BASE/'kfz';root.mkdir(parents=True,exist_ok=True)
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS kfz_vehicles(id INTEGER PRIMARY KEY,kind TEXT NOT NULL DEFAULT 'Auto',name TEXT NOT NULL,plate TEXT NOT NULL DEFAULT '',make TEXT NOT NULL DEFAULT '',model TEXT NOT NULL DEFAULT '',vin TEXT NOT NULL DEFAULT '',year INTEGER,first_registration TEXT,acquired TEXT,odometer INTEGER NOT NULL DEFAULT 0,hours REAL,inspection_due TEXT,inspection_notes TEXT NOT NULL DEFAULT '',insurance TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',archived INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS kfz_events(id INTEGER PRIMARY KEY,vehicle_id INTEGER NOT NULL REFERENCES kfz_vehicles(id) ON DELETE CASCADE,kind TEXT NOT NULL,title TEXT NOT NULL,event_date TEXT NOT NULL DEFAULT '',due_date TEXT NOT NULL DEFAULT '',due_km INTEGER,interval_months INTEGER,interval_km INTEGER,odometer INTEGER,hours REAL,materials TEXT NOT NULL DEFAULT '',workshop TEXT NOT NULL DEFAULT '',cost REAL,notes TEXT NOT NULL DEFAULT '',done INTEGER NOT NULL DEFAULT 0,archived INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS kfz_files(id INTEGER PRIMARY KEY,vehicle_id INTEGER NOT NULL REFERENCES kfz_vehicles(id) ON DELETE CASCADE,event_id INTEGER REFERENCES kfz_events(id) ON DELETE SET NULL,filename TEXT NOT NULL,stored TEXT NOT NULL,mime TEXT NOT NULL,created TEXT NOT NULL);
  ''')
 def check(req):writer(req);safe_post(req)
 def vehicle(c,vid):
  v=c.execute('SELECT * FROM kfz_vehicles WHERE id=?',(vid,)).fetchone()
  if not v:raise HTTPException(404,'Fahrzeug nicht gefunden')
  return v
 def event(c,eid):
  e=c.execute('SELECT * FROM kfz_events WHERE id=?',(eid,)).fetchone()
  if not e:raise HTTPException(404,'Eintrag nicht gefunden')
  return e
 def d(s):
  if not s:return None
  try:return date.fromisoformat(s).isoformat()
  except ValueError:raise HTTPException(400,'Ungültiges Datum')
 @app.get('/kfz',response_class=HTMLResponse)
 def page(req:Request,archive:int=0,vehicle_id:int=0):
  require(req)
  with db() as c:
   vehicles=c.execute('SELECT * FROM kfz_vehicles WHERE archived=? ORDER BY kind,name,id',(int(bool(archive)),)).fetchall()
   chosen=vehicle(c,vehicle_id) if vehicle_id else (vehicles[0] if vehicles else None)
   events=c.execute('SELECT * FROM kfz_events WHERE vehicle_id=? ORDER BY archived ASC,done ASC,COALESCE(due_date,event_date) ASC,id DESC',(chosen['id'],)).fetchall() if chosen else []
   docs=c.execute('SELECT * FROM kfz_files WHERE vehicle_id=? ORDER BY id DESC',(chosen['id'],)).fetchall() if chosen else []
  return render(req,'kfz.html',vehicles=vehicles,chosen=chosen,events=events,docs=docs,archive=bool(archive),today=date.today().isoformat())
 @app.post('/kfz/vehicle')
 def save_vehicle(req:Request,id:int=Form(0),kind:str=Form('Auto'),name:str=Form(...),plate:str=Form(''),make:str=Form(''),model:str=Form(''),vin:str=Form(''),year:str=Form(''),first_registration:str=Form(''),acquired:str=Form(''),odometer:int=Form(0),hours:str=Form(''),inspection_due:str=Form(''),inspection_notes:str=Form(''),insurance:str=Form(''),notes:str=Form('')):
  check(req)
  if kind not in ('Auto','Anhänger','Motorrad','Sonstiges'):raise HTTPException(400,'Ungültige Art')
  if not name.strip() or odometer<0:raise HTTPException(400,'Name und Kilometerstand prüfen')
  fields=(kind,name.strip()[:140],plate[:30],make[:100],model[:100],vin[:100],int(year) if year else None,d(first_registration),d(acquired),odometer,float(hours) if hours else None,d(inspection_due),inspection_notes[:2000],insurance[:1000],notes[:8000],now())
  with db() as c:
   if id:
    vehicle(c,id)
    c.execute('UPDATE kfz_vehicles SET kind=?,name=?,plate=?,make=?,model=?,vin=?,year=?,first_registration=?,acquired=?,odometer=?,hours=?,inspection_due=?,inspection_notes=?,insurance=?,notes=?,updated=? WHERE id=?',(*fields,id))
   else:id=c.execute('INSERT INTO kfz_vehicles(kind,name,plate,make,model,vin,year,first_registration,acquired,odometer,hours,inspection_due,inspection_notes,insurance,notes,updated,created) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(*fields,now())).lastrowid
  return go('/kfz?vehicle_id='+str(id))
 @app.post('/kfz/vehicle/{id}/action')
 def vehicle_action(req:Request,id:int,action:str=Form(...)):
  check(req)
  with db() as c:
   vehicle(c,id)
   if action in ('archive','restore'):c.execute('UPDATE kfz_vehicles SET archived=?,updated=? WHERE id=?',(int(action=='archive'),now(),id))
   elif action=='delete':
    files=c.execute('SELECT stored FROM kfz_files WHERE vehicle_id=?',(id,)).fetchall()
    c.execute('DELETE FROM kfz_vehicles WHERE id=?',(id,))
    for f in files:(root/f['stored']).unlink(missing_ok=True)
   else:raise HTTPException(400,'Ungültige Aktion')
  return go('/kfz?archive='+('1' if action=='archive' else '0'))
 @app.post('/kfz/event')
 def save_event(req:Request,vehicle_id:int=Form(...),id:int=Form(0),kind:str=Form('Wartung'),title:str=Form(...),event_date:str=Form(''),due_date:str=Form(''),due_km:str=Form(''),interval_months:str=Form(''),interval_km:str=Form(''),odometer:str=Form(''),hours:str=Form(''),materials:str=Form(''),workshop:str=Form(''),cost:str=Form(''),notes:str=Form(''),done:int=Form(0)):
  check(req)
  if kind not in ('Wartung','Reparatur','HU/TÜV','Prüfung','Reifen','Sonstiges'):raise HTTPException(400,'Ungültige Kategorie')
  if not title.strip():raise HTTPException(400,'Titel fehlt')
  def positive(v):
   if not v:return None
   n=int(v)
   if n<0:raise HTTPException(400,'Negative Werte unzulässig')
   return n
  fields=(kind,title.strip()[:200],d(event_date) or '',d(due_date) or '',positive(due_km),positive(interval_months),positive(interval_km),positive(odometer),float(hours) if hours else None,materials[:6000],workshop[:200],float(cost.replace(',','.')) if cost else None,notes[:8000],int(bool(done)),now())
  with db() as c:
   vehicle(c,vehicle_id)
   if id:
    e=event(c,id)
    if e['vehicle_id']!=vehicle_id:raise HTTPException(400,'Falsches Fahrzeug')
    c.execute('UPDATE kfz_events SET kind=?,title=?,event_date=?,due_date=?,due_km=?,interval_months=?,interval_km=?,odometer=?,hours=?,materials=?,workshop=?,cost=?,notes=?,done=?,updated=? WHERE id=?',(*fields,id))
   else:id=c.execute('INSERT INTO kfz_events(vehicle_id,kind,title,event_date,due_date,due_km,interval_months,interval_km,odometer,hours,materials,workshop,cost,notes,done,updated,created) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(vehicle_id,*fields,now())).lastrowid
  return go('/kfz?vehicle_id='+str(vehicle_id))
 @app.post('/kfz/event/{id}/action')
 def event_action(req:Request,id:int,action:str=Form(...)):
  check(req)
  with db() as c:
   e=event(c,id);vid=e['vehicle_id']
   if action in ('archive','restore'):c.execute('UPDATE kfz_events SET archived=?,updated=? WHERE id=?',(int(action=='archive'),now(),id))
   elif action=='toggle':c.execute('UPDATE kfz_events SET done=1-done,updated=? WHERE id=?',(now(),id))
   elif action=='delete':
    docs=c.execute('SELECT stored FROM kfz_files WHERE event_id=?',(id,)).fetchall()
    c.execute('DELETE FROM kfz_events WHERE id=?',(id,))
    for f in docs:(root/f['stored']).unlink(missing_ok=True)
   else:raise HTTPException(400,'Ungültige Aktion')
  return go('/kfz?vehicle_id='+str(vid))
 @app.post('/kfz/file')
 async def upload(req:Request,vehicle_id:int=Form(...),event_id:int=Form(0),file:UploadFile=File(...)):
  check(req)
  data=await file.read(12*1024*1024+1)
  if len(data)>12*1024*1024:raise HTTPException(413,'Datei größer als 12 MB')
  suffix=Path(file.filename or '').suffix.lower()
  if suffix not in ('.pdf','.jpg','.jpeg','.png','.webp'):raise HTTPException(400,'Nur PDF und Bilder')
  with db() as c:
   vehicle(c,vehicle_id)
   if event_id and event(c,event_id)['vehicle_id']!=vehicle_id:raise HTTPException(400,'Falscher Eintrag')
   stored=uuid4().hex+suffix;(root/stored).write_bytes(data)
   c.execute('INSERT INTO kfz_files(vehicle_id,event_id,filename,stored,mime,created) VALUES (?,?,?,?,?,?)',(vehicle_id,event_id or None,Path(file.filename or 'Datei').name[:200],stored,file.content_type or 'application/octet-stream',now()))
  return go('/kfz?vehicle_id='+str(vehicle_id))
 @app.get('/kfz/file/{id}')
 def get_file(req:Request,id:int):
  require(req)
  with db() as c:f=c.execute('SELECT * FROM kfz_files WHERE id=?',(id,)).fetchone()
  if not f:raise HTTPException(404)
  return FileResponse(root/f['stored'],filename=f['filename'],media_type='application/octet-stream',headers={'X-Content-Type-Options':'nosniff'})
 @app.post('/kfz/file/{id}/delete')
 def delete_file(req:Request,id:int):
  check(req)
  with db() as c:
   f=c.execute('SELECT * FROM kfz_files WHERE id=?',(id,)).fetchone()
   if not f:raise HTTPException(404)
   c.execute('DELETE FROM kfz_files WHERE id=?',(id,))
   (root/f['stored']).unlink(missing_ok=True)
  return go('/kfz?vehicle_id='+str(f['vehicle_id']))
 def build_vehicle_pdf(vid,target):
  with db() as c:
   v=vehicle(c,vid);events=c.execute('SELECT * FROM kfz_events WHERE vehicle_id=? ORDER BY event_date DESC,id DESC',(vid,)).fetchall();docs=c.execute('SELECT * FROM kfz_files WHERE vehicle_id=?',(vid,)).fetchall()
  font='Helvetica'
  for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/ttf/dejavu/DejaVuSans.ttf'):
   if Path(path).exists():
    if 'KFZUnicode' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('KFZUnicode',path))
    font='KFZUnicode';break
  styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='KfzTitle',fontName=font,fontSize=16,leading=21,spaceAfter=10));styles.add(ParagraphStyle(name='KfzSmall',fontName=font,fontSize=8,leading=12,spaceAfter=5));styles.add(ParagraphStyle(name='KfzHeading',fontName=font,fontSize=11,leading=15,spaceBefore=12,spaceAfter=7))
  def p(x):return Paragraph(html.escape(str(x if x is not None else '–')).replace('\n','<br/>'),styles['KfzSmall'])
  story=[Paragraph('Fahrzeugakte: '+html.escape(v['name']),styles['KfzTitle']),p('Typ: '+v['kind']+' | Kennzeichen: '+v['plate']+' | Stand: '+date.today().isoformat())]
  labels=[('Hersteller','make'),('Modell','model'),('FIN','vin'),('Baujahr','year'),('Erstzulassung','first_registration'),('Kaufdatum','acquired'),('Kilometerstand','odometer'),('Betriebsstunden','hours'),('HU/TÜV fällig','inspection_due'),('Hinweise HU','inspection_notes'),('Versicherung','insurance'),('Weitere Infos','notes')]
  for label,key in labels:
   if v[key] not in ('',None):story.append(p(label+': '+str(v[key])))
  story.append(Paragraph('Wartungen, Prüfungen und Reparaturen',styles['KfzHeading']))
  if not events:story.append(p('Keine Einträge'))
  for e in events:
   lines=[p(e['kind']+' · '+e['title']+' · '+('archiviert' if e['archived'] else 'aktiv')+' · '+('erledigt' if e['done'] else 'offen'))]
   for label,key in [('Datum','event_date'),('Fällig','due_date'),('Fällig bei km','due_km'),('Intervall Monate','interval_months'),('Intervall km','interval_km'),('KM bei Durchführung','odometer'),('Betriebsstunden','hours'),('Material / Teile','materials'),('Werkstatt / Ausführender','workshop'),('Kosten EUR','cost'),('Bemerkungen','notes')]:
    if e[key] not in ('',None):lines.append(p(label+': '+str(e[key])))
   lines.append(Spacer(1,4*mm));story.append(KeepTogether(lines))
  if docs:
   story.append(Paragraph('Angehängte Dokumente',styles['KfzHeading']))
   for doc in docs:story.append(p(doc['filename']))
  target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
  SimpleDocTemplate(str(target),pagesize=A4,leftMargin=17*mm,rightMargin=17*mm,topMargin=16*mm,bottomMargin=16*mm).build(story)
 @app.get('/kfz/vehicle/{id}/pdf')
 def pdf(req:Request,id:int):
  require(req)
  with db() as c:v=vehicle(c,id)
  path=root/('fahrzeugakte-'+str(id)+'.pdf');build_vehicle_pdf(id,path)
  return FileResponse(path,media_type='application/pdf',filename='KFZ-'+re.sub(r'[^a-zA-Z0-9_-]','-',v['name'])+'.pdf')
 return build_vehicle_pdf
