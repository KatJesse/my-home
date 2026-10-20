import os, re, json, uuid, sqlite3, hashlib, hmac, secrets, subprocess, shutil, tempfile, html, io, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from bs4 import BeautifulSoup, NavigableString, Tag
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage

BASE=Path(os.environ.get('HAUS_DATA','/tmp/haus-data'))
BASE.mkdir(parents=True,exist_ok=True)
FILES=BASE/'uploads'; FILES.mkdir(exist_ok=True)
DB=BASE/'house.db'
app=FastAPI(title='Mein Zuhause')
app.mount('/static',StaticFiles(directory=str(Path(__file__).parent/'static')),name='static')
tpl=Jinja2Templates(directory=str(Path(__file__).parent/'templates'))

def db():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA journal_mode=WAL'); return c
with db() as c:
 c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS sessions(tokenhash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL);
 CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,title TEXT NOT NULL,body TEXT NOT NULL,category_id INTEGER,owner_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',updated TEXT NOT NULL,created TEXT NOT NULL,FOREIGN KEY(category_id) REFERENCES categories(id));
 CREATE TABLE IF NOT EXISTS attachments(id TEXT PRIMARY KEY,note_id TEXT NOT NULL,name TEXT NOT NULL,mime TEXT NOT NULL,ocr TEXT NOT NULL DEFAULT '',width_mm INTEGER NOT NULL DEFAULT 140,FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE);
 CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY AUTOINCREMENT,note_id TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created TEXT NOT NULL);
 CREATE VIRTUAL TABLE IF NOT EXISTS note_search USING fts5(note_id UNINDEXED,title,body,ocr);''')
 for n in ['Allgemein','Versicherungen','Haus & Technik','Smart Home','Rezepte','Urlaub & Packlisten']:
  c.execute('INSERT OR IGNORE INTO categories(name) VALUES (?)',(n,))

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def hash_pw(p,salt=None):
 salt=salt or secrets.token_hex(16)
 return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),310000).hex()
def verify(p,v):
 try:
  salt,digest=v.split(':'); return hmac.compare_digest(hash_pw(p,salt).split(':')[1],digest)
 except Exception: return False

def user(req):
 tok=req.cookies.get('haus_session','')
 if not tok: return None
 with db() as c:
  return c.execute('SELECT users.* FROM users JOIN sessions ON sessions.user_id=users.id WHERE sessions.tokenhash=? AND sessions.expires>?',(hashlib.sha256(tok.encode()).hexdigest(),int(time.time()))).fetchone()
def require(req):
 u=user(req)
 if not u: raise HTTPException(401,'Bitte anmelden')
 return u

def safe_post(req):
 origin=req.headers.get('origin',''); host=req.headers.get('host','')
 if origin and origin.split('://')[-1]!=host: raise HTTPException(403,'Ungueltiger Ursprung')

def render(req,name,**kw):
 return tpl.TemplateResponse(name,{'request':req,'user':user(req),**kw})
def go(path): return RedirectResponse(path,status_code=303)

def cfg():
 p=Path('/data/options.json')
 try: return json.loads(p.read_text())
 except Exception: return {'pdf_directory':str(BASE/'pdf'),'ocr_languages':'deu+eng'}

def sync_search(c,nid):
 n=c.execute('SELECT * FROM notes WHERE id=?',(nid,)).fetchone()
 c.execute('DELETE FROM note_search WHERE note_id=?',(nid,))
 if n:
  att=c.execute('SELECT ocr FROM attachments WHERE note_id=?',(nid,)).fetchall()
  c.execute('INSERT INTO note_search VALUES (?,?,?,?)',(nid,n['title'],BeautifulSoup(n['body'],'html.parser').get_text(' ',strip=True),' '.join(a['ocr'] for a in att)))

def clean_html(value):
 soup=BeautifulSoup(value,'html.parser')
 allowed={'p','br','b','strong','i','em','u','h1','h2','h3','ul','ol','li','blockquote','table','thead','tbody','tr','td','th','a','div','span'}
 for tag in list(soup.find_all(True)):
  if tag.name not in allowed: tag.unwrap(); continue
  attrs={}
  if tag.name=='a' and tag.get('href','').startswith(('https://','http://','mailto:')): attrs['href']=tag['href']
  tag.attrs=attrs
 return str(soup)

def make_pdf(nid):
 with db() as c:
  n=c.execute('SELECT notes.*,categories.name category FROM notes LEFT JOIN categories ON categories.id=notes.category_id WHERE notes.id=?',(nid,)).fetchone()
  if not n: return
  at=c.execute('SELECT * FROM attachments WHERE note_id=?',(nid,)).fetchall()
 target=Path(cfg().get('pdf_directory','/share/mein-zuhause-pdf'))
 target.mkdir(parents=True,exist_ok=True)
 cat=re.sub(r'[^\w .-]','_',n['category'] or 'Allgemein').strip('. ') or 'Allgemein'
 directory=target/cat; directory.mkdir(parents=True,exist_ok=True)
 filename=re.sub(r'[^\w .-]','_',n['title']).strip('. ')[:90] or 'Notiz'
 out=directory/(filename+'-'+nid[:8]+'.pdf')
 if n['status']!='active':
  for p in target.glob('*/'+'*-'+nid[:8]+'.pdf'): p.unlink(missing_ok=True)
  return
 styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name='Haus',parent=styles['BodyText'],leading=15,spaceAfter=7))
 story=[Paragraph(html.escape(n['title']),styles['Title']),Paragraph(html.escape(n['category'] or ''),styles['Italic']),Spacer(1,7*mm)]
 soup=BeautifulSoup(n['body'],'html.parser')
 # Convert every text node, including top-level text and text inside nested containers.
 # Paragraph supports basic inline formatting, while block elements define breaks.
 blocks={'p','div','h1','h2','h3','li','blockquote','tr','ul','ol','table'}
 inline={'b','strong','i','em','u','a','span','td','th'}
 buffer=[]
 def flush(style_name='Haus',prefix=''):
  markup=''.join(buffer).strip()
  buffer.clear()
  if markup and BeautifulSoup(markup,'html.parser').get_text(' ',strip=True):
   story.append(Paragraph(prefix+markup,styles[style_name]))
 def walk(node,style_name='Haus',prefix=''):
  if isinstance(node,NavigableString):
   buffer.append(html.escape(str(node)))
   return
  if not isinstance(node,Tag): return
  tag=node.name
  if tag=='br':
   buffer.append('<br/>')
   return
  if tag in blocks:
   flush()
   current='Heading2' if tag in ('h1','h2') else 'Haus'
   lead='&#8226; ' if tag=='li' else ''
   for child in node.children:
    walk(child,current)
   flush(current,lead)
   return
  tagmap={'strong':'b','b':'b','em':'i','i':'i','u':'u'}
  if tag in tagmap: buffer.append('<'+tagmap[tag]+'>')
  for child in node.children: walk(child,style_name)
  if tag in tagmap: buffer.append('</'+tagmap[tag]+'>')
 for node in soup.contents:
  walk(node)
 flush()
 for a in at:
  path=FILES/a['id']
  if a['mime'].startswith('image/') and path.exists():
   try:
    with PILImage.open(path) as im:
     w,h=im.size
    width=min(a['width_mm'],170)*mm
    height=width*h/w
    if height>230*mm: height=230*mm; width=height*w/h
    story.extend([Spacer(1,4*mm),Paragraph(html.escape(a['name']),styles['Italic']),Image(str(path),width=width,height=height)])
   except Exception: pass
  else: story.append(Paragraph('Anhang: '+html.escape(a['name']),styles['Haus']))
 fd,tmp=tempfile.mkstemp(suffix='.pdf',dir=str(directory)); os.close(fd)
 try:
  SimpleDocTemplate(tmp,pagesize=(210*mm,297*mm),rightMargin=18*mm,leftMargin=18*mm,topMargin=20*mm,bottomMargin=20*mm).build(story)
  os.replace(tmp,out)
  for old in target.glob('*/'+'*-'+nid[:8]+'.pdf'):
   if old!=out: old.unlink(missing_ok=True)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)

@app.get('/',response_class=HTMLResponse)
def home(req:Request,q:str='',status:str='active'):
 if not user(req): return go('/login')
 with db() as c:
  if q:
   rows=c.execute('SELECT n.*,categories.name category FROM notes n LEFT JOIN categories ON categories.id=n.category_id WHERE n.status=? AND n.id IN (SELECT note_id FROM note_search WHERE note_search MATCH ?) ORDER BY n.updated DESC',(status,' '.join(re.findall(r'[\w]+',q))+'*' if re.findall(r'[\w]+',q) else 'zzzznonexistent')).fetchall()
  else: rows=c.execute('SELECT n.*,categories.name category FROM notes n LEFT JOIN categories ON categories.id=n.category_id WHERE n.status=? ORDER BY n.updated DESC',(status,)).fetchall()
  cats=c.execute('SELECT * FROM categories ORDER BY name').fetchall()
 return render(req,'home.html',notes=rows,categories=cats,q=q,status=status)
@app.get('/login',response_class=HTMLResponse)
def login_page(req:Request):
 with db() as c: count=c.execute('SELECT count(*) FROM users').fetchone()[0]
 return render(req,'login.html',first=count==0,error='')
@app.post('/login')
def login(req:Request,username:str=Form(...),password:str=Form(...)):
 safe_post(req)
 with db() as c:
  count=c.execute('SELECT count(*) FROM users').fetchone()[0]
  if not count:
   if len(password)<12: return render(req,'login.html',first=True,error='Mindestens 12 Zeichen verwenden')
   c.execute('INSERT INTO users(username,password,role) VALUES (?,?,?)',(username,hash_pw(password),'admin'))
  u=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
  if not u or not verify(password,u['password']): return render(req,'login.html',first=False,error='Anmeldung fehlgeschlagen')
  token=secrets.token_urlsafe(40)
  c.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],int(time.time())+30*86400))
 resp=go('/'); resp.set_cookie('haus_session',token,httponly=True,samesite='strict',secure=req.url.scheme=='https',max_age=30*86400); return resp
@app.post('/logout')
def logout(req:Request):
 safe_post(req); tok=req.cookies.get('haus_session','')
 with db() as c: c.execute('DELETE FROM sessions WHERE tokenhash=?',(hashlib.sha256(tok.encode()).hexdigest(),))
 r=go('/login');r.delete_cookie('haus_session');return r
@app.post('/users')
def add_user(req:Request,username:str=Form(...),password:str=Form(...)):
 safe_post(req); u=require(req)
 if u['role']!='admin': raise HTTPException(403)
 if len(password)<12: raise HTTPException(400,'Passwort zu kurz')
 with db() as c:
  try:c.execute('INSERT INTO users(username,password,role) VALUES (?,?,?)',(username,hash_pw(password),'member'))
  except sqlite3.IntegrityError: raise HTTPException(409,'Benutzer existiert')
 return go('/')
@app.post('/categories')
def add_category(req:Request,name:str=Form(...)):
 safe_post(req);require(req)
 with db() as c: c.execute('INSERT OR IGNORE INTO categories(name) VALUES (?)',(name.strip()[:80],))
 return go('/')
@app.get('/notes/new')
def new(req:Request):
 require(req)
 with db() as c: cats=c.execute('SELECT * FROM categories ORDER BY name').fetchall()
 return render(req,'edit.html',note=None,attachments=[],categories=cats)
@app.get('/notes/{nid}')
def edit(req:Request,nid:str):
 require(req)
 with db() as c:
  n=c.execute('SELECT * FROM notes WHERE id=?',(nid,)).fetchone()
  if not n: raise HTTPException(404)
  at=c.execute('SELECT * FROM attachments WHERE note_id=?',(nid,)).fetchall()
  cats=c.execute('SELECT * FROM categories ORDER BY name').fetchall()
 return render(req,'edit.html',note=n,attachments=at,categories=cats)
@app.post('/notes/save')
def save(req:Request,nid:str=Form(''),title:str=Form(...),body:str=Form(''),category_id:int=Form(...)):
 safe_post(req);u=require(req)
 nid=nid or uuid.uuid4().hex
 body=clean_html(body)
 with db() as c:
  old=c.execute('SELECT * FROM notes WHERE id=?',(nid,)).fetchone()
  if old:
   c.execute('INSERT INTO revisions(note_id,title,body,created) VALUES (?,?,?,?)',(nid,old['title'],old['body'],now()))
   c.execute('UPDATE notes SET title=?,body=?,category_id=?,updated=? WHERE id=?',(title[:180],body,category_id,now(),nid))
  else:c.execute('INSERT INTO notes(id,title,body,category_id,owner_id,updated,created) VALUES (?,?,?,?,?,?,?)',(nid,title[:180],body,category_id,u['id'],now(),now()))
  sync_search(c,nid)
 try: make_pdf(nid)
 except Exception as e: print('PDF export pending/error:',repr(e),flush=True)
 return go('/notes/'+nid)
@app.post('/notes/{nid}/status')
def status(req:Request,nid:str,value:str=Form(...)):
 safe_post(req);require(req)
 if value not in ('active','archived','trash'): raise HTTPException(400)
 with db() as c: c.execute('UPDATE notes SET status=?,updated=? WHERE id=?',(value,now(),nid))
 try:make_pdf(nid)
 except Exception as e:print('PDF export:',repr(e),flush=True)
 return go('/')
@app.post('/notes/{nid}/delete')
def delete(req:Request,nid:str):
 safe_post(req);require(req)
 with db() as c:
  n=c.execute('SELECT status FROM notes WHERE id=?',(nid,)).fetchone()
  if not n or n['status']!='trash':raise HTTPException(400,'Zuerst in den Papierkorb verschieben')
  ats=c.execute('SELECT id FROM attachments WHERE note_id=?',(nid,)).fetchall()
  c.execute('DELETE FROM notes WHERE id=?',(nid,));sync_search(c,nid)
 for a in ats:(FILES/a['id']).unlink(missing_ok=True)
 try:
  root=Path(cfg().get('pdf_directory','/share/mein-zuhause-pdf'))
  for p in root.glob('*/*-'+nid[:8]+'.pdf'):p.unlink(missing_ok=True)
 except Exception:pass
 return go('/')
@app.post('/notes/{nid}/upload')
async def upload(req:Request,nid:str,files:list[UploadFile]=File(...)):
 safe_post(req);require(req)
 with db() as c:
  if not c.execute('SELECT id FROM notes WHERE id=?',(nid,)).fetchone():raise HTTPException(404)
  for f in files:
   aid=uuid.uuid4().hex; dst=FILES/aid; size=0
   with dst.open('wb') as out:
    while chunk:=await f.read(1024*1024):
     size+=len(chunk)
     if size>20*1024*1024:dst.unlink(missing_ok=True);raise HTTPException(413,'Maximal 20 MB je Datei')
     out.write(chunk)
   mime=f.content_type or 'application/octet-stream'
   if mime not in ('application/pdf','image/png','image/jpeg','image/webp'):
    dst.unlink(missing_ok=True);raise HTTPException(415,'Nur PDF, PNG, JPEG, WebP')
   extracted=''
   try:
    if mime=='application/pdf':
     from pypdf import PdfReader
     extracted=' '.join(p.extract_text() or '' for p in PdfReader(str(dst)).pages[:30])[:100000]
     if len(extracted.strip())<30:
      with tempfile.TemporaryDirectory() as tmp:
       subprocess.run(['pdftoppm','-f','1','-l','10','-scale-to','1800','-png',str(dst),str(Path(tmp)/'page')],timeout=90,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
       extracted=' '.join(subprocess.run(['tesseract',str(p),'stdout','-l',cfg().get('ocr_languages','deu+eng')],capture_output=True,text=True,timeout=45).stdout for p in sorted(Path(tmp).glob('*.png')))
    else: extracted=subprocess.run(['tesseract',str(dst),'stdout','-l',cfg().get('ocr_languages','deu+eng')],capture_output=True,text=True,timeout=45).stdout
   except Exception as e:print('OCR warning',repr(e),flush=True)
   c.execute('INSERT INTO attachments(id,note_id,name,mime,ocr) VALUES (?,?,?,?,?)',(aid,nid,Path(f.filename or 'Datei').name[:180],mime,extracted[:100000]))
  sync_search(c,nid)
 try:make_pdf(nid)
 except Exception as e:print('PDF error',repr(e),flush=True)
 return go('/notes/'+nid)
@app.get('/attachments/{aid}')
def attachment(req:Request,aid:str):
 require(req)
 with db() as c:a=c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone()
 if not a:raise HTTPException(404)
 return FileResponse(FILES/aid,media_type=a['mime'],filename=a['name'],content_disposition_type='inline' if a['mime'].startswith('image/') or a['mime']=='application/pdf' else 'attachment',headers={'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox"})
@app.post('/attachments/{aid}/width')
def width(req:Request,aid:str,width_mm:int=Form(...)):
 safe_post(req);require(req)
 if not 20<=width_mm<=170:raise HTTPException(400)
 with db() as c:
  a=c.execute('SELECT note_id FROM attachments WHERE id=?',(aid,)).fetchone()
  if not a:raise HTTPException(404)
  c.execute('UPDATE attachments SET width_mm=? WHERE id=?',(width_mm,aid))
 try:make_pdf(a['note_id'])
 except Exception as e:print('PDF error',repr(e),flush=True)
 return go('/notes/'+a['note_id'])
@app.post('/attachments/{aid}/delete')
def del_attachment(req:Request,aid:str):
 safe_post(req);require(req)
 with db() as c:
  a=c.execute('SELECT note_id FROM attachments WHERE id=?',(aid,)).fetchone()
  if not a:raise HTTPException(404)
  c.execute('DELETE FROM attachments WHERE id=?',(aid,));sync_search(c,a['note_id'])
 (FILES/aid).unlink(missing_ok=True)
 try:make_pdf(a['note_id'])
 except Exception:pass
 return go('/notes/'+a['note_id'])
@app.get('/health')
def health(req:Request):
 require(req);return {'status':'ok','pdf_directory':cfg().get('pdf_directory')}
