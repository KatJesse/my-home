import sqlite3, shutil, json, uuid
from urllib.parse import urlencode
from datetime import date, timedelta
from pathlib import Path
from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

def install_features(app,db,require,writer,safe_post,render,go,now,BASE,FILES,hash_pw,cfg):
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS hidden_categories(user_id INTEGER NOT NULL,category_id INTEGER NOT NULL,PRIMARY KEY(user_id,category_id));
  CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS pantry_locations(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
  CREATE TABLE IF NOT EXISTS pantry_shelves(id INTEGER PRIMARY KEY,location_id INTEGER NOT NULL REFERENCES pantry_locations(id) ON DELETE CASCADE,name TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS pantry_categories(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
  CREATE TABLE IF NOT EXISTS pantry_items(id INTEGER PRIMARY KEY,name TEXT NOT NULL,quantity REAL,unit TEXT,minimum REAL,category_id INTEGER REFERENCES pantry_categories(id) ON DELETE SET NULL,shelf_id INTEGER REFERENCES pantry_shelves(id) ON DELETE SET NULL,expires TEXT,frozen TEXT,opened INTEGER NOT NULL DEFAULT 0,used_amount REAL,notes TEXT NOT NULL DEFAULT '',barcode TEXT NOT NULL DEFAULT '',updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS shopping(id INTEGER PRIMARY KEY,name TEXT NOT NULL,quantity REAL,unit TEXT,store TEXT NOT NULL DEFAULT '',position INTEGER NOT NULL DEFAULT 0,checked INTEGER NOT NULL DEFAULT 0,pantry_id INTEGER REFERENCES pantry_items(id) ON DELETE SET NULL);
  CREATE TABLE IF NOT EXISTS shopping_archives(id INTEGER PRIMARY KEY,closed_at TEXT NOT NULL,store TEXT NOT NULL DEFAULT '',item_count INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS shopping_archive_items(id INTEGER PRIMARY KEY,archive_id INTEGER NOT NULL REFERENCES shopping_archives(id) ON DELETE CASCADE,name TEXT NOT NULL,quantity REAL,unit TEXT,store TEXT,position INTEGER,checked INTEGER,pantry_id INTEGER);
  CREATE TABLE IF NOT EXISTS storage_places(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
  CREATE TABLE IF NOT EXISTS storage_boxes(id INTEGER PRIMARY KEY,number TEXT NOT NULL UNIQUE,title TEXT NOT NULL,place_id INTEGER REFERENCES storage_places(id) ON DELETE SET NULL,keywords TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',metadata TEXT NOT NULL DEFAULT '',image_id TEXT,updated TEXT NOT NULL);
  ''')
  c.execute("INSERT OR IGNORE INTO app_settings VALUES ('expiry_days','14')")
  c.execute("UPDATE users SET role='writer' WHERE role='member'")
 def admin(req):
  u=require(req)
  if u['role']!='admin':raise HTTPException(403,'Administratorrechte erforderlich')
  return u
 def check(req,write=True):
  safe_post(req)
  return writer(req) if write else require(req)
 def asfloat(s):
  if s is None or str(s).strip()=='':return None
  try:return float(str(s).replace(',','.'))
  except ValueError:raise HTTPException(400,'Ungueltige Zahl')
 def asdate(s):
  if not s:return None
  try:return date.fromisoformat(s).isoformat()
  except ValueError:raise HTTPException(400,'Ungueltiges Datum')
 def settings(c):return {r['key']:r['value'] for r in c.execute('SELECT * FROM app_settings')}
 def pantry_context(c):
  return dict(locations=c.execute('SELECT * FROM pantry_locations ORDER BY name').fetchall(),shelves=c.execute('SELECT s.*,l.name location FROM pantry_shelves s JOIN pantry_locations l ON l.id=s.location_id ORDER BY l.name,s.name').fetchall(),pcats=c.execute('SELECT * FROM pantry_categories ORDER BY name').fetchall())
 @app.get('/pantry',response_class=HTMLResponse)
 def pantry(req:Request,q:str='',category:int=0,location:int=0,expiry:str='',sort:str='name'):
  require(req)
  with db() as c:
   ctx=pantry_context(c); opts=settings(c);days=int(opts.get('expiry_days','14')); limit=(date.today()+timedelta(days=days)).isoformat();today=date.today().isoformat()
   rows=c.execute('''SELECT p.*,pc.name category,s.name shelf,l.name location FROM pantry_items p LEFT JOIN pantry_categories pc ON pc.id=p.category_id LEFT JOIN pantry_shelves s ON s.id=p.shelf_id LEFT JOIN pantry_locations l ON l.id=s.location_id''').fetchall()
  rows=[r for r in rows if (not q or q.casefold() in (' '.join(str(r[k] or '') for k in ('name','notes','barcode','category','location','shelf'))).casefold()) and (not category or r['category_id']==category) and (not location or any(x['id']==r['shelf_id'] and x['location_id']==location for x in ctx['shelves'])) and (not expiry or (expiry=='expired' and r['expires'] and r['expires']<today) or (expiry=='soon' and r['expires'] and today<=r['expires']<=limit) or (expiry=='low' and r['minimum'] is not None and (r['quantity'] or 0)<=r['minimum']))]
  rows=sorted(rows,key=lambda r:((r['expires'] or '9999') if sort=='expires' else (r['location'] or '').casefold() if sort=='location' else r['name'].casefold()))
  return render(req,'pantry.html',show_low_button=opts.get('show_low_button','yes')=='yes',items=rows,q=q,category=category,location=location,expiry=expiry,sort=sort,days=days,today=today,limit=limit,**ctx)
 @app.post('/pantry/locations')
 def add_location(req:Request,name:str=Form(...)):
  check(req)
  with db() as c:c.execute('INSERT OR IGNORE INTO pantry_locations(name) VALUES (?)',(name.strip()[:100],))
  return go('/pantry')
 @app.post('/pantry/locations/{lid}')
 def location_update(req:Request,lid:int,name:str=Form(''),action:str=Form('save')):
  check(req)
  with db() as c:
   if action=='delete':c.execute('DELETE FROM pantry_locations WHERE id=?',(lid,))
   else:c.execute('UPDATE pantry_locations SET name=? WHERE id=?',(name.strip()[:100],lid))
  return go('/pantry')
 @app.post('/pantry/shelves')
 def add_shelf(req:Request,location_id:int=Form(...),name:str=Form(...)):
  check(req)
  with db() as c:c.execute('INSERT INTO pantry_shelves(location_id,name) VALUES (?,?)',(location_id,name.strip()[:100]))
  return go('/pantry')
 @app.post('/pantry/shelves/{sid}')
 def shelf_update(req:Request,sid:int,name:str=Form(''),location_id:int=Form(0),action:str=Form('save')):
  check(req)
  with db() as c:
   if action=='delete':c.execute('DELETE FROM pantry_shelves WHERE id=?',(sid,))
   else:c.execute('UPDATE pantry_shelves SET name=?,location_id=? WHERE id=?',(name.strip()[:100],location_id,sid))
  return go('/pantry')
 @app.post('/pantry/categories')
 def add_pcat(req:Request,name:str=Form(...)):
  check(req)
  with db() as c:c.execute('INSERT OR IGNORE INTO pantry_categories(name) VALUES (?)',(name.strip()[:100],))
  return go('/pantry')
 @app.post('/pantry/categories/{cid}')
 def pcat_update(req:Request,cid:int,name:str=Form(''),action:str=Form('save')):
  check(req)
  with db() as c:
   if action=='delete':c.execute('DELETE FROM pantry_categories WHERE id=?',(cid,))
   else:c.execute('UPDATE pantry_categories SET name=? WHERE id=?',(name.strip()[:100],cid))
  return go('/pantry')
 @app.get('/pantry/item',response_class=HTMLResponse)
 def pantry_edit(req:Request,id:int=0):
  require(req)
  with db() as c:
   item=c.execute('SELECT * FROM pantry_items WHERE id=?',(id,)).fetchone() if id else None
   return render(req,'pantry_edit.html',item=item,**pantry_context(c))
 @app.post('/pantry/item')
 def pantry_save(req:Request,id:int=Form(0),name:str=Form(...),quantity:str=Form(''),unit:str=Form(''),minimum:str=Form(''),category_id:int=Form(0),shelf_id:int=Form(0),expires:str=Form(''),frozen:str=Form(''),opened:str=Form(''),used_amount:str=Form(''),notes:str=Form(''),barcode:str=Form('')):
  check(req)
  if not name.strip():raise HTTPException(400,'Bezeichnung erforderlich')
  vals=(name.strip()[:180],asfloat(quantity),unit.strip()[:30],asfloat(minimum),category_id or None,shelf_id or None,asdate(expires),asdate(frozen),int(opened=='yes'),asfloat(used_amount),notes[:5000],barcode[:120],now())
  with db() as c:
   if id:c.execute('''UPDATE pantry_items SET name=?,quantity=?,unit=?,minimum=?,category_id=?,shelf_id=?,expires=?,frozen=?,opened=?,used_amount=?,notes=?,barcode=?,updated=? WHERE id=?''',vals+(id,))
   else:c.execute('''INSERT INTO pantry_items(name,quantity,unit,minimum,category_id,shelf_id,expires,frozen,opened,used_amount,notes,barcode,updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',vals)
  return go('/pantry')
 @app.post('/pantry/item/{id}/delete')
 def pantry_delete(req:Request,id:int):
  check(req)
  with db() as c:c.execute('DELETE FROM pantry_items WHERE id=?',(id,))
  return go('/pantry')
 @app.post('/pantry/item/{id}/shopping')
 def pantry_to_shop(req:Request,id:int):
  check(req)
  with db() as c:
   r=c.execute('SELECT * FROM pantry_items WHERE id=?',(id,)).fetchone()
   if not r:raise HTTPException(404)
   c.execute('INSERT INTO shopping(name,quantity,unit,position,pantry_id) VALUES (?,?,?,?,?)',(r['name'],max(0,(r['minimum'] or 1)-(r['quantity'] or 0)),r['unit'],c.execute('SELECT COALESCE(MAX(position),0)+1 FROM shopping').fetchone()[0],id))
  return go('/shopping')
 @app.post('/pantry/shopping/low')
 def low_to_shop(req:Request):
  check(req)
  with db() as c:
   for r in c.execute('SELECT * FROM pantry_items WHERE minimum IS NOT NULL AND COALESCE(quantity,0)<=minimum').fetchall():
    if not c.execute('SELECT 1 FROM shopping WHERE pantry_id=? AND checked=0',(r['id'],)).fetchone():c.execute('INSERT INTO shopping(name,quantity,unit,position,pantry_id) VALUES (?,?,?,?,?)',(r['name'],max(0,r['minimum']-(r['quantity'] or 0)),r['unit'],c.execute('SELECT COALESCE(MAX(position),0)+1 FROM shopping').fetchone()[0],r['id']))
  return go('/shopping')
 @app.get('/shopping',response_class=HTMLResponse)
 def shopping(req:Request,store:str='',sort:str='manual',direction:str='asc'):
  require(req)
  with db() as c:
   rows=c.execute('SELECT * FROM shopping ORDER BY position ASC,id ASC').fetchall();stores=[r[0] for r in c.execute("SELECT DISTINCT store FROM shopping WHERE store!='' ORDER BY store")]
  visible=[r for r in rows if not store or (r['store']=='' if store=='__none__' else r['store']==store)]
  if sort in ('name','store','quantity'):
   visible=sorted(visible,key=lambda r:((r[sort] or '').casefold() if sort!='quantity' else (r['quantity'] if r['quantity'] is not None else float('-inf')),r['position'],r['id']),reverse=direction=='desc')
  # Abgehakte Artikel immer nach unten, unabhaengig von der gewaehlten Sortierung.
  visible=sorted(visible,key=lambda r:r['checked'])
  return render(req,'shopping.html',items=visible,stores=stores,store=store,sort=sort,direction=direction)
 @app.post('/shopping')
 def shopping_add(req:Request,name:str=Form(...),quantity:str=Form(''),unit:str=Form(''),store:str=Form('')):
  check(req)
  with db() as c:c.execute('INSERT INTO shopping(name,quantity,unit,store,position) VALUES (?,?,?,?,?)',(name.strip()[:180],asfloat(quantity),unit[:30],store[:100],c.execute('SELECT COALESCE(MAX(position),0)+1 FROM shopping').fetchone()[0]))
  return go('/shopping')
 @app.post('/shopping/close')
 def shopping_close(req:Request,store:str=Form(''),scope:str=Form('all')):
  check(req)
  with db() as c:
   rows=c.execute('SELECT * FROM shopping WHERE store=? ORDER BY position,id',('' if store=='__none__' else store,)).fetchall() if store else c.execute('SELECT * FROM shopping ORDER BY position,id').fetchall()
   if scope not in ('all','checked'):raise HTTPException(400,'Ungueltiger Archivmodus')
   if scope=='checked':rows=[r for r in rows if r['checked']]
   if not rows:return go('/shopping'+('?' + urlencode({'store':store}) if store else ''))
   archive_store=store or ('Verschiedene Geschäfte' if len({r['store'] for r in rows})>1 else rows[0]['store'])
   cur=c.execute('INSERT INTO shopping_archives(closed_at,store,item_count) VALUES (?,?,?)',(now(),archive_store,len(rows)))
   for r in rows:c.execute('INSERT INTO shopping_archive_items(archive_id,name,quantity,unit,store,position,checked,pantry_id) VALUES (?,?,?,?,?,?,?,?)',(cur.lastrowid,r['name'],r['quantity'],r['unit'],r['store'],r['position'],r['checked'],r['pantry_id']))
   c.executemany('DELETE FROM shopping WHERE id=?',[(r['id'],) for r in rows])
  return go('/shopping'+('?' + urlencode({'store':store}) if store else ''))
 @app.post('/shopping/reorder')
 async def shopping_reorder(req:Request):
  check(req);safe_post(req)
  form=await req.form();store=str(form.get('store',''))
  raw=str(form.get('order',''))
  try:ids=[int(x) for x in raw.split(',') if x]
  except ValueError:raise HTTPException(400,'Ungueltige Reihenfolge')
  if len(ids)!=len(set(ids)):raise HTTPException(400,'Doppelte Eintraege')
  with db() as c:
   rows=c.execute('SELECT id,store FROM shopping').fetchall()
   visible={r['id'] for r in rows if not store or (r['store']=='' if store=='__none__' else r['store']==store)}
   if set(ids)!=visible:raise HTTPException(409,'Liste hat sich geaendert, bitte neu laden')
   all_ids=[r['id'] for r in c.execute('SELECT id FROM shopping ORDER BY position,id')]
   it=iter(ids);new_order=[next(it) if x in visible else x for x in all_ids]
   for pos,ident in enumerate(new_order,1):c.execute('UPDATE shopping SET position=? WHERE id=?',(pos,ident))
  return go('/shopping'+('?' + urlencode({'store':store}) if store else ''))
 @app.post('/shopping/{id}')
 def shopping_change(req:Request,id:int,action:str=Form('save'),name:str=Form(''),quantity:str=Form(''),unit:str=Form(''),store:str=Form(''),checked:str=Form(''),filter_store:str=Form('')):
  check(req)
  with db() as c:
   if action=='delete':c.execute('DELETE FROM shopping WHERE id=?',(id,))
   elif action in ('up','down'):
    r=c.execute('SELECT * FROM shopping WHERE id=?',(id,)).fetchone()
    if r:
     other=c.execute('SELECT * FROM shopping WHERE (position,id) '+('<' if action=='up' else '>')+' (?,?) ORDER BY position '+('DESC' if action=='up' else 'ASC')+',id '+('DESC' if action=='up' else 'ASC')+' LIMIT 1',(r['position'],id)).fetchone()
     if other:c.execute('UPDATE shopping SET position=? WHERE id=?',(other['position'],id));c.execute('UPDATE shopping SET position=? WHERE id=?',(r['position'],other['id']))
   else:c.execute('UPDATE shopping SET name=?,quantity=?,unit=?,store=?,checked=? WHERE id=?',(name.strip()[:180],asfloat(quantity),unit[:30],store[:100],int(checked=='yes'),id))
  return go('/shopping'+('?' + urlencode({'store':filter_store}) if filter_store else ''))
 @app.post('/shopping/{id}/toggle')
 def shopping_toggle(req:Request,id:int,store:str=Form('')):
  check(req)
  with db() as c:c.execute('UPDATE shopping SET checked=CASE WHEN checked=1 THEN 0 ELSE 1 END WHERE id=?',(id,))
  return go('/shopping'+('?' + urlencode({'store':store}) if store else ''))
 @app.get('/shopping/archive',response_class=HTMLResponse)
 def shopping_archive(req:Request):
  require(req)
  with db() as c:
   archives=c.execute('SELECT * FROM shopping_archives ORDER BY closed_at DESC,id DESC').fetchall()
   contents={r['id']:c.execute('SELECT * FROM shopping_archive_items WHERE archive_id=? ORDER BY position,id',(r['id'],)).fetchall() for r in archives}
  return render(req,'shopping_archive.html',archives=archives,contents=contents)
 @app.post('/shopping/archive/{id}/delete')
 def shopping_archive_delete(req:Request,id:int):
  check(req)
  with db() as c:
   c.execute('DELETE FROM shopping_archive_items WHERE archive_id=?',(id,))
   c.execute('DELETE FROM shopping_archives WHERE id=?',(id,))
  return go('/shopping/archive')
 @app.post('/shopping/archive/{id}/restore')
 def shopping_restore(req:Request,id:int):
  check(req)
  with db() as c:
   rows=c.execute('SELECT * FROM shopping_archive_items WHERE archive_id=? ORDER BY position,id',(id,)).fetchall()
   for r in rows:c.execute('INSERT INTO shopping(name,quantity,unit,store,position,checked,pantry_id) VALUES (?,?,?,?,?,?,?)',(r['name'],r['quantity'],r['unit'],r['store'],c.execute('SELECT COALESCE(MAX(position),0)+1 FROM shopping').fetchone()[0],r['checked'],r['pantry_id'] if r['pantry_id'] and c.execute('SELECT 1 FROM pantry_items WHERE id=?',(r['pantry_id'],)).fetchone() else None))
   c.execute('DELETE FROM shopping_archive_items WHERE archive_id=?',(id,))
   c.execute('DELETE FROM shopping_archives WHERE id=?',(id,))
  return go('/shopping')
 @app.get('/storage',response_class=HTMLResponse)
 def storage(req:Request,q:str='',place:int=0):
  require(req)
  with db() as c:
   places=c.execute('SELECT * FROM storage_places ORDER BY name').fetchall()
   rows=c.execute('SELECT b.*,p.name place FROM storage_boxes b LEFT JOIN storage_places p ON p.id=b.place_id ORDER BY b.number').fetchall()
  rows=[r for r in rows if (not place or r['place_id']==place) and (not q or q.casefold() in ' '.join(str(r[k] or '') for k in ('number','title','keywords','notes','metadata','place')).casefold())]
  return render(req,'storage.html',items=rows,places=places,q=q,place=place)
 @app.post('/storage/places')
 def storage_place(req:Request,name:str=Form(...)):
  check(req)
  with db() as c:c.execute('INSERT OR IGNORE INTO storage_places(name) VALUES (?)',(name.strip()[:100],))
  return go('/storage')
 @app.post('/storage/places/{id}')
 def storage_place_change(req:Request,id:int,name:str=Form(''),action:str=Form('save')):
  check(req)
  with db() as c:
   if action=='delete':c.execute('DELETE FROM storage_places WHERE id=?',(id,))
   else:c.execute('UPDATE storage_places SET name=? WHERE id=?',(name.strip()[:100],id))
  return go('/storage')
 @app.get('/storage/box',response_class=HTMLResponse)
 def storage_box(req:Request,id:int=0):
  require(req)
  with db() as c:
   box=c.execute('SELECT * FROM storage_boxes WHERE id=?',(id,)).fetchone() if id else None
   places=c.execute('SELECT * FROM storage_places ORDER BY name').fetchall()
  return render(req,'storage_edit.html',item=box,places=places)
 @app.post('/storage/box')
 def storage_box_save(req:Request,id:int=Form(0),number:str=Form(...),title:str=Form(...),place_id:int=Form(0),keywords:str=Form(''),notes:str=Form(''),metadata:str=Form('')):
  check(req)
  if not number.strip() or not title.strip():raise HTTPException(400,'Nummer und Bezeichnung erforderlich')
  vals=(number.strip()[:70],title.strip()[:180],place_id or None,keywords[:2000],notes[:10000],metadata[:5000],now())
  try:
   with db() as c:
    if id:c.execute('UPDATE storage_boxes SET number=?,title=?,place_id=?,keywords=?,notes=?,metadata=?,updated=? WHERE id=?',vals+(id,))
    else:c.execute('INSERT INTO storage_boxes(number,title,place_id,keywords,notes,metadata,updated) VALUES (?,?,?,?,?,?,?)',vals)
  except sqlite3.IntegrityError:raise HTTPException(409,'Kistennummer bereits vergeben')
  return go('/storage')
 @app.post('/storage/box/{id}/delete')
 def storage_box_delete(req:Request,id:int):
  check(req)
  with db() as c:
   r=c.execute('SELECT image_id FROM storage_boxes WHERE id=?',(id,)).fetchone()
   c.execute('DELETE FROM storage_boxes WHERE id=?',(id,))
  if r and r['image_id']:(FILES/r['image_id']).unlink(missing_ok=True)
  return go('/storage')
 from fastapi import UploadFile,File
 @app.post('/storage/box/{id}/image')
 async def storage_image(req:Request,id:int,file:UploadFile=File(...)):
  check(req)
  if file.content_type not in ('image/png','image/jpeg','image/webp'):raise HTTPException(415,'Nur Bilder')
  data=await file.read(10*1024*1024+1)
  if len(data)>10*1024*1024:raise HTTPException(413)
  with db() as c:
   r=c.execute('SELECT image_id FROM storage_boxes WHERE id=?',(id,)).fetchone()
   if not r:raise HTTPException(404)
   fid=uuid.uuid4().hex;(FILES/fid).write_bytes(data)
   c.execute('UPDATE storage_boxes SET image_id=? WHERE id=?',(fid,id))
  if r['image_id']:(FILES/r['image_id']).unlink(missing_ok=True)
  return go('/storage/box?id='+str(id))
 @app.get('/storage/image/{id}')
 def storage_image_get(req:Request,id:int):
  require(req)
  with db() as c:r=c.execute('SELECT image_id FROM storage_boxes WHERE id=?',(id,)).fetchone()
  if not r or not r['image_id']:raise HTTPException(404)
  
  path=FILES/r['image_id']
  head=path.open('rb').read(16)
  mime='image/png' if head.startswith(b'\x89PNG') else 'image/webp' if head.startswith(b'RIFF') and head[8:12]==b'WEBP' else 'image/jpeg' if head.startswith(b'\xff\xd8') else 'application/octet-stream'
  return FileResponse(path,media_type=mime,headers={'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox"})
 def media_list():
  with db() as c:
   attachments=c.execute("SELECT a.id,a.name,a.mime,n.title AS owner FROM attachments a LEFT JOIN notes n ON n.id=a.note_id WHERE a.mime LIKE 'image/%' ORDER BY a.name").fetchall()
   boxes=c.execute("SELECT id,image_id,number,title FROM storage_boxes WHERE image_id IS NOT NULL ORDER BY number").fetchall()
  result=[]
  for a in attachments:
   path=FILES/a['id']; result.append(dict(kind='attachment',id=a['id'],name=a['name'],owner=a['owner'] or '',date=__import__('datetime').datetime.fromtimestamp(path.stat().st_mtime).strftime('%d.%m.%Y %H:%M') if path.exists() else 'Datei fehlt',url='/attachments/'+a['id']))
  for b in boxes:
   path=FILES/b['image_id'];result.append(dict(kind='box',id=str(b['id']),name='Kiste '+b['number'],owner=b['title'],date=__import__('datetime').datetime.fromtimestamp(path.stat().st_mtime).strftime('%d.%m.%Y %H:%M') if path.exists() else 'Datei fehlt',url='/storage/image/'+str(b['id'])))
  return result
 @app.post('/settings/media/{kind}/{id}/delete')
 def media_delete(req:Request,kind:str,id:str):
  admin(req);safe_post(req)
  if kind=='attachment':
   with db() as c:
    a=c.execute('SELECT id,note_id FROM attachments WHERE id=?',(id,)).fetchone()
    if not a:raise HTTPException(404)
    c.execute('DELETE FROM attachments WHERE id=?',(id,))
    # Keep OCR search synchronized
    from bs4 import BeautifulSoup
    n=c.execute('SELECT title,body FROM notes WHERE id=?',(a['note_id'],)).fetchone()
    if n:
     c.execute('DELETE FROM note_search WHERE note_id=?',(a['note_id'],))
     ocr=' '.join(x[0] for x in c.execute('SELECT ocr FROM attachments WHERE note_id=?',(a['note_id'],)))
     c.execute('INSERT INTO note_search VALUES (?,?,?,?)',(a['note_id'],n['title'],BeautifulSoup(n['body'],'html.parser').get_text(' ',strip=True),ocr))
   (FILES/id).unlink(missing_ok=True)
  elif kind=='box':
   with db() as c:
    a=c.execute('SELECT image_id FROM storage_boxes WHERE id=?',(int(id),)).fetchone()
    if not a or not a['image_id']:raise HTTPException(404)
    c.execute('UPDATE storage_boxes SET image_id=NULL WHERE id=?',(int(id),))
   (FILES/a['image_id']).unlink(missing_ok=True)
  else:raise HTTPException(404)
  return go('/settings#media')
 @app.post('/settings/appearance')
 async def appearance_save(req:Request):
  admin(req);safe_post(req)
  data=await req.form()
  pages=('notes','pantry','shopping','storage','plotten','tasks','food','kfz','settings')
  keys={'font','columns','gap','rowgap','menugap','bold','fields','stripe1','stripe2'}
  with db() as c:
   for page in pages:
    for device in ('desktop','mobile'):
     for key in keys:
      field=f'layout_{page}_{device}_{key}'
      if field in data:
       value=str(data[field])[:120]
       if key in ('font','gap','rowgap','menugap'):
        try:value=str(max(0,min(80,int(value))))
        except ValueError:raise HTTPException(400,'Ungueltiger Zahlenwert')
       if key=='columns' and value not in ('1','2','3','4'):raise HTTPException(400,'Spaltenzahl ungueltig')
       if key in ('stripe1','stripe2'):
        import re
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise HTTPException(400,'Farbwert ungueltig')
       if key in ('bold','fields'):
        allowed={'notes':('title','category','updated'),'pantry':('name','location','shelf','quantity'),'shopping':('name','quantity','store'),'storage':('number','title','place'),'settings':('title',),'plotten':('name','manufacturer','kind','size','quantity','status'),'tasks':('title',),'food':('title','category','updated'),'kfz':('title',)}[page]
        value=','.join(v for v in value.split(',') if v in allowed)
       c.execute('INSERT INTO app_settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(field,value))
   for page in pages:
    key='hide_tab_'+page
    c.execute('INSERT INTO app_settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,'yes' if key in data else 'no'))
   c.execute("INSERT INTO app_settings(key,value) VALUES ('show_plot_summary',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",('yes' if 'show_plot_summary' in data else 'no',))
   import re
   color=str(data.get('food_remove_color','#8b95a3'))
   if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise HTTPException(400,'Ungueltige Farbe')
   try:food_gap=max(0,min(120,int(data.get('food_week_gap','26'))))
   except ValueError:raise HTTPException(400,'Ungueltiger Abstand')
   for key,value in [('food_remove_color',color),('food_week_gap',str(food_gap))]:
    c.execute('INSERT INTO app_settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
   c.execute("INSERT INTO app_settings(key,value) VALUES ('show_low_button',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",('yes' if 'show_low_button' in data else 'no',))
  return go('/settings#appearance')
 @app.get('/settings',response_class=HTMLResponse)
 def setting_page(req:Request):
  require(req)
  with db() as c:
   users=c.execute('SELECT id,username,role FROM users ORDER BY username').fetchall()
   cats=c.execute('SELECT * FROM categories ORDER BY name').fetchall()
   hidden={r[0] for r in c.execute('SELECT category_id FROM hidden_categories WHERE user_id=?',(require(req)['id'],))}
   opts=settings(c)
  disk=shutil.disk_usage(BASE)
  return render(req,'settings.html',media_items=media_list(),users=users,categories=cats,hidden=hidden,opts=opts,disk=disk,usage_pct=round(disk.used/disk.total*100,1) if disk.total else 0,pdf_path=cfg().get('pdf_directory',''),nas={k:v for k,v in opts.items() if k.startswith('nas_') and k!='nas_password'},nas_password_set=bool(opts.get('nas_password')))
 @app.post('/settings/nas')
 def nas_save(req:Request,mode:str=Form('local'),server:str=Form(''),share:str=Form(''),folder:str=Form(''),username:str=Form(''),password:str=Form('')):
  admin(req);safe_post(req)
  if mode not in ('local','smb'):raise HTTPException(400,'Ungueltiger Speichermodus')
  if mode=='smb':
   import re
   if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}',server):raise HTTPException(400,'SMB-Server ungueltig')
   if not re.fullmatch(r'[A-Za-z0-9_. -]{1,100}',share):raise HTTPException(400,'Freigabename ungueltig')
   if not username or any(x in username for x in ('\n','\r')):raise HTTPException(400,'Benutzername ungueltig')
   if password and any(x in password for x in ('\n','\r')):raise HTTPException(400,'Passwort ungueltig')
   if any(part in ('.','..') for part in folder.replace('\\','/').split('/')):raise HTTPException(400,'Unterordner ungueltig')
  values={'nas_mode':mode,'nas_server':server.strip(),'nas_share':share.strip(),'nas_folder':folder.strip('/'),'nas_user':username.strip()}
  if password:values['nas_password']=password
  with db() as c:
   for key,value in values.items():c.execute('INSERT INTO app_settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
  return go('/settings')
 @app.post('/settings/user/{id}')
 def update_user(req:Request,id:int,role:str=Form(...)):
  admin(req);safe_post(req)
  if role not in ('admin','writer','reader'):raise HTTPException(400)
  with db() as c:
   current=c.execute('SELECT role FROM users WHERE id=?',(id,)).fetchone()
   if not current:raise HTTPException(404)
   if current['role']=='admin' and role!='admin' and c.execute("SELECT count(*) FROM users WHERE role='admin'").fetchone()[0]<=1:raise HTTPException(400,'Letzten Administrator nicht entfernen')
   c.execute('UPDATE users SET role=? WHERE id=?',(role,id))
  return go('/settings')
 @app.post('/settings/user/{id}/delete')
 def delete_user(req:Request,id:int):
  admin(req);safe_post(req)
  if require(req)['id']==id:raise HTTPException(400,'Eigenes Konto nicht loeschen')
  with db() as c:
   if c.execute("SELECT role FROM users WHERE id=?",(id,)).fetchone() is None:raise HTTPException(404)
   c.execute('DELETE FROM sessions WHERE user_id=?',(id,));c.execute('DELETE FROM hidden_categories WHERE user_id=?',(id,));c.execute('DELETE FROM users WHERE id=?',(id,))
  return go('/settings')
 @app.post('/settings/categories/visibility')
 def category_visibility(req:Request,category_id:int=Form(...),visible:str=Form('')):
  safe_post(req);u=require(req)
  with db() as c:
   c.execute('DELETE FROM hidden_categories WHERE user_id=? AND category_id=?',(u['id'],category_id))
   if visible!='yes':c.execute('INSERT INTO hidden_categories VALUES (?,?)',(u['id'],category_id))
  return go('/settings')
 @app.post('/settings/expiry')
 def expiry_days(req:Request,days:int=Form(...)):
  check(req)
  if not 0<=days<=365:raise HTTPException(400)
  with db() as c:c.execute("INSERT INTO app_settings(key,value) VALUES ('expiry_days',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(days),))
  return go('/settings')
