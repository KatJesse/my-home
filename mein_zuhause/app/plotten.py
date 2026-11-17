"""Plotten: Auftraege, Reservierungen, Warenbewegungen und Inventur."""
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse

STATUSES=('plotted','weeded','pressed','paid','delivered')

def install_plotten(app,db,require,writer,safe_post,render,go,now):
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS plot_stock(id INTEGER PRIMARY KEY,manufacturer TEXT NOT NULL,kind TEXT NOT NULL,size TEXT NOT NULL,color TEXT NOT NULL DEFAULT '',quantity INTEGER NOT NULL DEFAULT 0,UNIQUE(manufacturer,kind,size,color));
  CREATE TABLE IF NOT EXISTS plot_orders(id INTEGER PRIMARY KEY,customer TEXT NOT NULL,manufacturer TEXT NOT NULL,kind TEXT NOT NULL,size TEXT NOT NULL,color TEXT NOT NULL DEFAULT '',quantity INTEGER NOT NULL CHECK(quantity>0),unit_cents INTEGER NOT NULL DEFAULT 0,plotted INTEGER NOT NULL DEFAULT 0,weeded INTEGER NOT NULL DEFAULT 0,pressed INTEGER NOT NULL DEFAULT 0,paid INTEGER NOT NULL DEFAULT 0,delivered INTEGER NOT NULL DEFAULT 0,archived INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS plot_purchases(id INTEGER PRIMARY KEY,order_date TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',created TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS plot_purchase_items(id INTEGER PRIMARY KEY,purchase_id INTEGER NOT NULL REFERENCES plot_purchases(id) ON DELETE CASCADE,stock_id INTEGER NOT NULL REFERENCES plot_stock(id),quantity INTEGER NOT NULL CHECK(quantity>0),unit_cents INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS plot_movements(id INTEGER PRIMARY KEY,stock_id INTEGER NOT NULL REFERENCES plot_stock(id),delta INTEGER NOT NULL,reason TEXT NOT NULL,ref_id INTEGER,created TEXT NOT NULL);
  ''')
 with db() as c:
  c.execute('PRAGMA foreign_keys=OFF')
  for table in ('plot_stock','plot_orders'):
   cols={r['name'] for r in c.execute(f'PRAGMA table_info({table})')}
   if 'color' not in cols:
    c.execute(f"ALTER TABLE {table} ADD COLUMN color TEXT NOT NULL DEFAULT ''")
  # Migration is idempotent: once-per-database marker.
  c.execute("CREATE TABLE IF NOT EXISTS plot_schema_migrations (name TEXT PRIMARY KEY)")
  if not c.execute("SELECT 1 FROM plot_schema_migrations WHERE name='unit_status_027'").fetchone():
   for field in STATUSES:
    c.execute(f'UPDATE plot_orders SET {field}=quantity WHERE {field}=1 AND quantity>1')
   c.execute("INSERT INTO plot_schema_migrations(name) VALUES ('unit_status_027')")
  if not c.execute("SELECT 1 FROM plot_schema_migrations WHERE name='stock_color_unique_027'").fetchone():
   # Rebuild to remove the legacy UNIQUE(manufacturer,kind,size) constraint.
   c.execute("CREATE TABLE plot_stock_new (id INTEGER PRIMARY KEY,manufacturer TEXT NOT NULL,kind TEXT NOT NULL,size TEXT NOT NULL,color TEXT NOT NULL DEFAULT '',quantity INTEGER NOT NULL DEFAULT 0,UNIQUE(manufacturer,kind,size,color))")
   c.execute('INSERT INTO plot_stock_new(id,manufacturer,kind,size,color,quantity) SELECT id,manufacturer,kind,size,color,quantity FROM plot_stock')
   c.execute('DROP TABLE plot_stock')
   c.execute('ALTER TABLE plot_stock_new RENAME TO plot_stock')
   c.execute("INSERT INTO plot_schema_migrations(name) VALUES ('stock_color_unique_027')")
  c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_plot_stock_color ON plot_stock(manufacturer,kind,size,color)')
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
 def stock(c,m,k,s,color):
  c.execute('INSERT OR IGNORE INTO plot_stock(manufacturer,kind,size,color) VALUES (?,?,?,?)',(m,k,s,color))
  return c.execute('SELECT id FROM plot_stock WHERE manufacturer=? AND kind=? AND size=? AND color=?',(m,k,s,color)).fetchone()['id']
 def move(c,sid,delta,reason,ref=None):
  if delta:
   c.execute('UPDATE plot_stock SET quantity=quantity+? WHERE id=?',(delta,sid))
   c.execute('INSERT INTO plot_movements(stock_id,delta,reason,ref_id,created) VALUES (?,?,?,?,?)',(sid,delta,reason,ref,now()))
 def context(c):
  rows=c.execute('''SELECT s.*,COALESCE((SELECT SUM(o.quantity-o.pressed) FROM plot_orders o WHERE o.manufacturer=s.manufacturer AND o.kind=s.kind AND o.size=s.size AND o.color=s.color AND o.archived=0),0) reserved FROM plot_stock s ORDER BY manufacturer,kind,color,size''').fetchall()
  return rows
 @app.get('/plotten',response_class=HTMLResponse)
 def plot_page(req:Request,q:str='',filter:str='',view:str='active',tab:str='orders'):
  require(req)
  if filter not in ('','plotted','weeded','pressed','paid','delivered'):filter=''
  if view not in ('active','archive'):view='active'
  if tab not in ('orders','lager','bestellungen','inventur'):tab='orders'
  with db() as c:
   sql='SELECT * FROM plot_orders WHERE archived=?';args=[int(view=='archive')]
   if q:sql+=' AND (customer LIKE ? OR manufacturer LIKE ? OR kind LIKE ? OR size LIKE ? OR color LIKE ? OR notes LIKE ?)';args += ['%'+q+'%']*6
   if filter:sql+=' AND '+filter+'<quantity'
   orders=c.execute(sql+' ORDER BY id DESC',args).fetchall()
   purchases=c.execute('SELECT * FROM plot_purchases ORDER BY order_date DESC,id DESC LIMIT 30').fetchall()
   details={r['id']:c.execute('''SELECT i.*,s.manufacturer,s.kind,s.size,s.color FROM plot_purchase_items i JOIN plot_stock s ON s.id=i.stock_id WHERE purchase_id=?''',(r['id'],)).fetchall() for r in purchases}
   return render(req,'plotten.html',orders=orders,stocks=context(c),purchases=purchases,purchase_details=details,q=q,filter=filter,view=view,statuses=STATUSES,tab=tab)
 @app.post('/plotten/order')
 def order_save(req:Request,id:int=Form(0),customer:str=Form(...),manufacturer:str=Form(...),kind:str=Form(...),size:str=Form(...),color:str=Form(...),quantity:str=Form(...),unit_price:str=Form('0'),notes:str=Form('')):
  check(req); name,m,k,s,clr=map(txt,(customer,manufacturer,kind,size,color));qty=integer(quantity,1);price=cents(unit_price)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if id:
    old=c.execute('SELECT * FROM plot_orders WHERE id=?',(id,)).fetchone()
    if not old:raise HTTPException(404,'Auftrag nicht gefunden')
    if old['archived']:raise HTTPException(409,'Archivierten Auftrag zuerst wiederherstellen')
    if old['pressed']:
     oldsid=stock(c,old['manufacturer'],old['kind'],old['size'],old['color'])
     move(c,oldsid,old['pressed'],'Auftragskorrektur Rueckbuchung',id)
    c.execute('''UPDATE plot_orders SET customer=?,manufacturer=?,kind=?,size=?,color=?,quantity=?,unit_cents=?,notes=?,updated=? WHERE id=?''',(name,m,k,s,clr,qty,price,notes[:2000],now(),id))
    for field in STATUSES:
     c.execute(f'UPDATE plot_orders SET {field}=MIN({field},?) WHERE id=?',(qty,id))
    new_pressed=min(old['pressed'],qty)
    if new_pressed:move(c,stock(c,m,k,s,clr),-new_pressed,'Auftragskorrektur Entnahme',id)
   else:
    c.execute('''INSERT INTO plot_orders(customer,manufacturer,kind,size,color,quantity,unit_cents,notes,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?)''',(name,m,k,s,clr,qty,price,notes[:2000],now(),now()))
  return go('/plotten')
 @app.post('/plotten/order/{oid}/status')
 def order_status(req:Request,oid:int,field:str=Form(...),count:str=Form(...)):
  check(req)
  if field not in STATUSES:raise HTTPException(400,'Unbekannter Status')
  val=integer(count,0)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   o=c.execute('SELECT * FROM plot_orders WHERE id=?',(oid,)).fetchone()
   if not o:raise HTTPException(404,'Auftrag nicht gefunden')
   if o['archived']:raise HTTPException(409,'Auftrag ist archiviert')
   if val>o['quantity']:raise HTTPException(400,'Bearbeitete Anzahl darf die Auftragsmenge nicht ueberschreiten')
   if field=='pressed' and o[field]!=val:
    sid=stock(c,o['manufacturer'],o['kind'],o['size'],o['color'])
    move(c,sid,o[field]-val,'Pressen' if val>o[field] else 'Pressen rueckgaengig',oid)
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
    if not all(o[x]>=o['quantity'] for x in STATUSES):raise HTTPException(409,'Nur vollstaendig abgeschlossene Auftraege archivieren')
    c.execute('UPDATE plot_orders SET archived=1 WHERE id=?',(oid,))
   elif action=='restore':c.execute('UPDATE plot_orders SET archived=0 WHERE id=?',(oid,))
   else:
    if o['pressed']:move(c,stock(c,o['manufacturer'],o['kind'],o['size'],o['color']),o['pressed'],'Auftrag geloescht Rueckbuchung',oid)
    c.execute('DELETE FROM plot_orders WHERE id=?',(oid,))
  return go('/plotten')
 @app.post('/plotten/purchase')
 def purchase(req:Request,order_date:str=Form(...),notes:str=Form(''),manufacturer:list[str]=Form(...),kind:list[str]=Form(...),size:list[str]=Form(...),color:list[str]=Form(...),quantity:list[str]=Form(...),unit_price:list[str]=Form(...)):
  check(req)
  try:date.fromisoformat(order_date)
  except ValueError:raise HTTPException(400,'Ungueltiges Bestelldatum')
  if not len(manufacturer)==len(kind)==len(size)==len(color)==len(quantity)==len(unit_price):raise HTTPException(400,'Unvollstaendige Bestellpositionen')
  items=[(txt(m),txt(k),txt(s),txt(clr),integer(q,1),cents(price)) for m,k,s,clr,q,price in zip(manufacturer,kind,size,color,quantity,unit_price) if m.strip() or k.strip() or s.strip() or q.strip()]
  if not items:raise HTTPException(400,'Mindestens eine Bestellposition erforderlich')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   pid=c.execute('INSERT INTO plot_purchases(order_date,notes,created) VALUES (?,?,?)',(order_date,notes[:1000],now())).lastrowid
   for m,k,s,clr,qty,price in items:
    sid=stock(c,m,k,s,clr)
    c.execute('INSERT INTO plot_purchase_items(purchase_id,stock_id,quantity,unit_cents) VALUES (?,?,?,?)',(pid,sid,qty,price))
    move(c,sid,qty,'Bestellung',pid)
  return go('/plotten?tab=bestellungen')
 @app.post('/plotten/inventory')
 def inventory(req:Request,stock_id:int=Form(0),manufacturer:str=Form(''),kind:str=Form(''),size:str=Form(''),color:str=Form(''),actual:str=Form(...)):
  check(req);qty=integer(actual)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   sid=stock_id or stock(c,txt(manufacturer),txt(kind),txt(size),txt(color))
   r=c.execute('SELECT quantity FROM plot_stock WHERE id=?',(sid,)).fetchone()
   if not r:raise HTTPException(404,'Lagerposition nicht gefunden')
   move(c,sid,qty-r['quantity'],'Inventur')
  return go('/plotten?tab=inventur')

 @app.post('/plotten/stock/{sid}/edit')
 def stock_edit(req:Request,sid:int,manufacturer:str=Form(...),kind:str=Form(...),size:str=Form(...),color:str=Form(...)):
  check(req);m,k,sz,clr=map(txt,(manufacturer,kind,size,color))
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   old=c.execute('SELECT * FROM plot_stock WHERE id=?',(sid,)).fetchone()
   if not old:raise HTTPException(404,'Lagerposition nicht gefunden')
   conflict=c.execute('SELECT id FROM plot_stock WHERE manufacturer=? AND kind=? AND size=? AND color=? AND id<>?',(m,k,sz,clr,sid)).fetchone()
   if conflict:raise HTTPException(409,'Lagerposition existiert bereits')
   # Keep linked orders and their reservations in sync with stock identity.
   c.execute('UPDATE plot_stock SET manufacturer=?,kind=?,size=?,color=? WHERE id=?',(m,k,sz,clr,sid))
   c.execute('UPDATE plot_orders SET manufacturer=?,kind=?,size=?,color=? WHERE manufacturer=? AND kind=? AND size=? AND color=?',(m,k,sz,clr,old['manufacturer'],old['kind'],old['size'],old['color']))
  return go('/plotten?tab=lager')
