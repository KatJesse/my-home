"""Plotten: Auftraege, Reservierungen, Warenbewegungen und Inventur."""
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse

STATUSES=('plotted','weeded','pressed','paid','delivered')

def install_plotten(app,db,require,writer,safe_post,render,go,now):
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS plot_stock(id INTEGER PRIMARY KEY,manufacturer TEXT NOT NULL,kind TEXT NOT NULL,size TEXT NOT NULL,quantity INTEGER NOT NULL DEFAULT 0,UNIQUE(manufacturer,kind,size));
  CREATE TABLE IF NOT EXISTS plot_orders(id INTEGER PRIMARY KEY,customer TEXT NOT NULL,manufacturer TEXT NOT NULL,kind TEXT NOT NULL,size TEXT NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0),unit_cents INTEGER NOT NULL DEFAULT 0,plotted INTEGER NOT NULL DEFAULT 0,weeded INTEGER NOT NULL DEFAULT 0,pressed INTEGER NOT NULL DEFAULT 0,paid INTEGER NOT NULL DEFAULT 0,delivered INTEGER NOT NULL DEFAULT 0,archived INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS plot_purchases(id INTEGER PRIMARY KEY,order_date TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',created TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS plot_purchase_items(id INTEGER PRIMARY KEY,purchase_id INTEGER NOT NULL REFERENCES plot_purchases(id) ON DELETE CASCADE,stock_id INTEGER NOT NULL REFERENCES plot_stock(id),quantity INTEGER NOT NULL CHECK(quantity>0),unit_cents INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS plot_movements(id INTEGER PRIMARY KEY,stock_id INTEGER NOT NULL REFERENCES plot_stock(id),delta INTEGER NOT NULL,reason TEXT NOT NULL,ref_id INTEGER,created TEXT NOT NULL);
  ''')
 def check(req):safe_post(req);writer(req)
 def integer(value,minimum=None):
  try: n=int(str(value).strip())
  except (ValueError,TypeError):raise HTTPException(400,'Ungueltige Anzahl')
  if minimum is not None and n<minimum:raise HTTPException(400,'Anzahl zu klein')
  return n
 def cents(value):
  try: d=Decimal(str(value).strip().replace(',','.')); n=int((d*100).quantize(Decimal('1')))
  except (InvalidOperation,ValueError):raise HTTPException(400,'Ungueltiger Preis')
  if n<0 or d*100!=n:raise HTTPException(400,'Preis muss positiv sein und maximal zwei Nachkommastellen haben')
  return n
 def txt(value):
  v=value.strip()[:120]
  if not v:raise HTTPException(400,'Hersteller, Textilart, Groesse und Name erforderlich')
  return v
 def stock(c,m,k,s):
  c.execute('INSERT OR IGNORE INTO plot_stock(manufacturer,kind,size) VALUES (?,?,?)',(m,k,s))
  return c.execute('SELECT id FROM plot_stock WHERE manufacturer=? AND kind=? AND size=?',(m,k,s)).fetchone()['id']
 def move(c,sid,delta,reason,ref=None):
  if delta:
   c.execute('UPDATE plot_stock SET quantity=quantity+? WHERE id=?',(delta,sid))
   c.execute('INSERT INTO plot_movements(stock_id,delta,reason,ref_id,created) VALUES (?,?,?,?,?)',(sid,delta,reason,ref,now()))
 def context(c):
  rows=c.execute('''SELECT s.*,COALESCE((SELECT SUM(o.quantity) FROM plot_orders o WHERE o.manufacturer=s.manufacturer AND o.kind=s.kind AND o.size=s.size AND o.pressed=0),0) reserved FROM plot_stock s ORDER BY manufacturer,kind,size''').fetchall()
  return rows
 @app.get('/plotten',response_class=HTMLResponse)
 def plot_page(req:Request,q:str='',filter:str='',view:str='active'):
  require(req)
  if filter not in ('','plotted','weeded','pressed','paid','delivered'):filter=''
  if view not in ('active','archive'):view='active'
  with db() as c:
   sql='SELECT * FROM plot_orders WHERE archived=?';args=[int(view=='archive')]
   if q:sql+=' AND (customer LIKE ? OR manufacturer LIKE ? OR kind LIKE ? OR size LIKE ? OR notes LIKE ?)';args += ['%'+q+'%']*5
   if filter:sql+=' AND '+filter+'=0'
   orders=c.execute(sql+' ORDER BY id DESC',args).fetchall()
   purchases=c.execute('SELECT * FROM plot_purchases ORDER BY order_date DESC,id DESC LIMIT 30').fetchall()
   details={r['id']:c.execute('''SELECT i.*,s.manufacturer,s.kind,s.size FROM plot_purchase_items i JOIN plot_stock s ON s.id=i.stock_id WHERE purchase_id=?''',(r['id'],)).fetchall() for r in purchases}
   return render(req,'plotten.html',orders=orders,stocks=context(c),purchases=purchases,purchase_details=details,q=q,filter=filter,view=view,statuses=STATUSES)
 @app.post('/plotten/order')
 def order_save(req:Request,id:int=Form(0),customer:str=Form(...),manufacturer:str=Form(...),kind:str=Form(...),size:str=Form(...),quantity:str=Form(...),unit_price:str=Form('0'),notes:str=Form('')):
  check(req); name,m,k,s=map(txt,(customer,manufacturer,kind,size));qty=integer(quantity,1);price=cents(unit_price)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if id:
    old=c.execute('SELECT * FROM plot_orders WHERE id=?',(id,)).fetchone()
    if not old:raise HTTPException(404,'Auftrag nicht gefunden')
    if old['archived']:raise HTTPException(409,'Archivierten Auftrag zuerst wiederherstellen')
    if old['pressed']:
     oldsid=stock(c,old['manufacturer'],old['kind'],old['size'])
     move(c,oldsid,old['quantity'],'Auftragskorrektur Rueckbuchung',id)
    c.execute('''UPDATE plot_orders SET customer=?,manufacturer=?,kind=?,size=?,quantity=?,unit_cents=?,notes=?,updated=? WHERE id=?''',(name,m,k,s,qty,price,notes[:2000],now(),id))
    if old['pressed']:move(c,stock(c,m,k,s),-qty,'Auftragskorrektur Entnahme',id)
   else:
    c.execute('''INSERT INTO plot_orders(customer,manufacturer,kind,size,quantity,unit_cents,notes,created,updated) VALUES (?,?,?,?,?,?,?,?,?)''',(name,m,k,s,qty,price,notes[:2000],now(),now()))
  return go('/plotten')
 @app.post('/plotten/order/{oid}/status')
 def order_status(req:Request,oid:int,field:str=Form(...),checked:str=Form('')):
  check(req)
  if field not in STATUSES:raise HTTPException(400,'Unbekannter Status')
  val=int(checked=='yes')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   o=c.execute('SELECT * FROM plot_orders WHERE id=?',(oid,)).fetchone()
   if not o:raise HTTPException(404,'Auftrag nicht gefunden')
   if o['archived']:raise HTTPException(409,'Auftrag ist archiviert')
   if field=='pressed' and o[field]!=val:
    sid=stock(c,o['manufacturer'],o['kind'],o['size'])
    move(c,sid,-o['quantity'] if val else o['quantity'],'Pressen' if val else 'Pressen rueckgaengig',oid)
   c.execute(f'UPDATE plot_orders SET {field}=?,updated=? WHERE id=?',(val,now(),oid))
  return go('/plotten')
 @app.post('/plotten/order/{oid}/archive')
 def order_archive(req:Request,oid:int,action:str=Form('archive')):
  check(req)
  if action not in ('archive','restore','delete'):raise HTTPException(400,'Unbekannte Aktion')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   o=c.execute('SELECT * FROM plot_orders WHERE id=?',(oid,)).fetchone()
   if not o:raise HTTPException(404,'Auftrag nicht gefunden')
   if action=='archive':
    if not all(o[x] for x in STATUSES):raise HTTPException(409,'Nur vollstaendig abgeschlossene Auftraege archivieren')
    c.execute('UPDATE plot_orders SET archived=1 WHERE id=?',(oid,))
   elif action=='restore':c.execute('UPDATE plot_orders SET archived=0 WHERE id=?',(oid,))
   else:
    if o['pressed']:move(c,stock(c,o['manufacturer'],o['kind'],o['size']),o['quantity'],'Auftrag geloescht Rueckbuchung',oid)
    c.execute('DELETE FROM plot_orders WHERE id=?',(oid,))
  return go('/plotten')
 @app.post('/plotten/purchase')
 def purchase(req:Request,order_date:str=Form(...),notes:str=Form(''),manufacturer:list[str]=Form(...),kind:list[str]=Form(...),size:list[str]=Form(...),quantity:list[str]=Form(...),unit_price:list[str]=Form(...)):
  check(req)
  try:date.fromisoformat(order_date)
  except ValueError:raise HTTPException(400,'Ungueltiges Bestelldatum')
  if not len(manufacturer)==len(kind)==len(size)==len(quantity)==len(unit_price):raise HTTPException(400,'Unvollstaendige Bestellpositionen')
  items=[(txt(m),txt(k),txt(s),integer(q,1),cents(price)) for m,k,s,q,price in zip(manufacturer,kind,size,quantity,unit_price) if m.strip() or k.strip() or s.strip() or q.strip()]
  if not items:raise HTTPException(400,'Mindestens eine Bestellposition erforderlich')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   pid=c.execute('INSERT INTO plot_purchases(order_date,notes,created) VALUES (?,?,?)',(order_date,notes[:1000],now())).lastrowid
   for m,k,s,qty,price in items:
    sid=stock(c,m,k,s)
    c.execute('INSERT INTO plot_purchase_items(purchase_id,stock_id,quantity,unit_cents) VALUES (?,?,?,?)',(pid,sid,qty,price))
    move(c,sid,qty,'Bestellung',pid)
  return go('/plotten#bestellungen')
 @app.post('/plotten/inventory')
 def inventory(req:Request,stock_id:int=Form(0),manufacturer:str=Form(''),kind:str=Form(''),size:str=Form(''),actual:str=Form(...)):
  check(req);qty=integer(actual)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   sid=stock_id or stock(c,txt(manufacturer),txt(kind),txt(size))
   r=c.execute('SELECT quantity FROM plot_stock WHERE id=?',(sid,)).fetchone()
   if not r:raise HTTPException(404,'Lagerposition nicht gefunden')
   move(c,sid,qty-r['quantity'],'Inventur')
  return go('/plotten#lager')
