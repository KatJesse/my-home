"""Independent task lists with archive and editable checklist items."""
from fastapi import Request,Form,HTTPException
from datetime import date
from fastapi.responses import HTMLResponse

def install_tasks(app,db,require,writer,safe_post,render,go,now):
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS task_lists(id INTEGER PRIMARY KEY,title TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',archived INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS task_items(id INTEGER PRIMARY KEY,list_id INTEGER NOT NULL REFERENCES task_lists(id) ON DELETE CASCADE,title TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',done INTEGER NOT NULL DEFAULT 0,position INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE INDEX IF NOT EXISTS idx_task_items_list ON task_items(list_id,done,position,id);
  ''')
  columns={r['name'] for r in c.execute('PRAGMA table_info(task_items)')}
  if 'due_date' not in columns:c.execute('ALTER TABLE task_items ADD COLUMN due_date TEXT DEFAULT NULL')
  if 'item_archived' not in columns:c.execute('ALTER TABLE task_items ADD COLUMN item_archived INTEGER NOT NULL DEFAULT 0')
  if 'parent_id' not in columns:c.execute('ALTER TABLE task_items ADD COLUMN parent_id INTEGER REFERENCES task_items(id) ON DELETE CASCADE')
 def check(req):writer(req);safe_post(req)
 def valid_list(c,id):
  row=c.execute('SELECT * FROM task_lists WHERE id=?',(id,)).fetchone()
  if not row:raise HTTPException(404,'Liste nicht gefunden')
  return row
 def valid_item(c,id):
  row=c.execute('SELECT * FROM task_items WHERE id=?',(id,)).fetchone()
  if not row:raise HTTPException(404,'Aufgabe nicht gefunden')
  return row
 @app.get('/tasks',response_class=HTMLResponse)
 def page(req:Request,list_id:int=0,archive:int=0,items_archive:int=0):
  require(req)
  with db() as c:
   lists=c.execute('SELECT l.*, (SELECT COUNT(*) FROM task_items i WHERE i.list_id=l.id AND i.item_archived=0 AND i.parent_id IS NULL) total, (SELECT COUNT(*) FROM task_items i WHERE i.list_id=l.id AND i.done=1 AND i.item_archived=0 AND i.parent_id IS NULL) done_count FROM task_lists l WHERE archived=? ORDER BY updated DESC,id DESC',(int(bool(archive)),)).fetchall()
   if list_id:
    selected=valid_list(c,list_id)
    if selected['archived']!=int(bool(archive)):return go('/tasks?archive='+str(int(bool(selected['archived'])))+'&list_id='+str(list_id))
   else:selected=lists[0] if lists else None
   items=c.execute('SELECT * FROM task_items WHERE list_id=? AND item_archived=? AND parent_id IS NULL ORDER BY done ASC,position ASC,id ASC',(selected['id'],int(bool(items_archive)))).fetchall() if selected else []
   children={}
   if selected:
    for child in c.execute('SELECT * FROM task_items WHERE list_id=? AND parent_id IS NOT NULL AND item_archived=? ORDER BY done ASC,position ASC,id ASC',(selected['id'],int(bool(items_archive)))).fetchall():children.setdefault(child['parent_id'],[]).append(child)
  archived_children={}
  if selected and not items_archive:
   with db() as c:
    for child in c.execute('SELECT * FROM task_items WHERE list_id=? AND parent_id IS NOT NULL AND item_archived=1 ORDER BY position,id',(selected['id'],)).fetchall():archived_children.setdefault(child['parent_id'],[]).append(child)
  today=date.today()
  days_left={i['id']:(date.fromisoformat(i['due_date'])-today).days if i['due_date'] else None for i in [*items,*(child for group in children.values() for child in group)]}
  return render(req,'tasks.html',lists=lists,selected=selected,items=items,archive=bool(archive),items_archive=bool(items_archive),days_left=days_left,children=children,archived_children=archived_children)
 @app.post('/tasks/list')
 def list_save(req:Request,id:int=Form(0),title:str=Form(...),notes:str=Form('')):
  check(req);title=title.strip()[:160]
  if not title:raise HTTPException(400,'Titel erforderlich')
  with db() as c:
   if id:
    l=valid_list(c,id)
    if l['archived']:raise HTTPException(409,'Archivierte Liste zuerst wiederherstellen')
    c.execute('UPDATE task_lists SET title=?,notes=?,updated=? WHERE id=?',(title,notes[:3000],now(),id))
   else:id=c.execute('INSERT INTO task_lists(title,notes,created,updated) VALUES (?,?,?,?)',(title,notes[:3000],now(),now())).lastrowid
  return go('/tasks?list_id='+str(id))
 @app.post('/tasks/list/{id}/action')
 def list_action(req:Request,id:int,action:str=Form(...)):
  check(req)
  with db() as c:
   l=valid_list(c,id)
   if action=='archive':c.execute('UPDATE task_lists SET archived=1,updated=? WHERE id=?',(now(),id))
   elif action=='restore':c.execute('UPDATE task_lists SET archived=0,updated=? WHERE id=?',(now(),id))
   elif action=='delete':c.execute('DELETE FROM task_lists WHERE id=?',(id,))
   else:raise HTTPException(400,'Ungueltige Aktion')
  return go('/tasks?archive='+('1' if action=='archive' else '0'))
 @app.post('/tasks/reorder')
 def reorder(req:Request,list_id:int=Form(...),order:str=Form(...)):
  check(req)
  with db() as c:
   l=valid_list(c,list_id)
   if l['archived']:raise HTTPException(409,'Archivierte Liste')
   actual={r['id'] for r in c.execute('SELECT id FROM task_items WHERE list_id=? AND item_archived=0 AND parent_id IS NULL',(list_id,))}
   try:ids=[int(x) for x in order.split(',') if x]
   except ValueError:raise HTTPException(400,'Ungültige Sortierung')
   if len(ids)!=len(actual) or set(ids)!=actual:raise HTTPException(400,'Aufgabenliste wurde geändert; bitte neu laden')
   for n,ident in enumerate(ids,1):c.execute('UPDATE task_items SET position=?,updated=? WHERE id=?',(n,now(),ident))
  return go('/tasks?list_id='+str(list_id))
 @app.post('/tasks/item')
 def item_save(req:Request,list_id:int=Form(...),id:int=Form(0),title:str=Form(...),notes:str=Form(''),due_date:str=Form(''),parent_id:int=Form(0)):
  check(req);title=title.strip()[:300]
  if due_date:
   try:due_date=date.fromisoformat(due_date).isoformat()
   except ValueError:raise HTTPException(400,'Ungültiges Fälligkeitsdatum')
  if not title:raise HTTPException(400,'Aufgabe darf nicht leer sein')
  with db() as c:
   l=valid_list(c,list_id)
   if l['archived']:raise HTTPException(409,'Liste ist archiviert')
   if parent_id:
    parent=valid_item(c,parent_id)
    if parent['list_id']!=list_id or parent['parent_id'] is not None or parent['item_archived']:raise HTTPException(400,'Ungültige Hauptaufgabe')
   if id:
    i=valid_item(c,id)
    if i['list_id']!=list_id:raise HTTPException(400,'Falsche Liste')
    if (i['parent_id'] or 0)!=parent_id:raise HTTPException(400,'Falsche Hauptaufgabe')
    c.execute('UPDATE task_items SET title=?,notes=?,due_date=?,updated=? WHERE id=?',(title,notes[:3000],due_date or None,now(),id))
   else:
    pos=c.execute('SELECT COALESCE(MAX(position),0)+1 FROM task_items WHERE list_id=? AND item_archived=0 AND parent_id IS NULL',(list_id,)).fetchone()[0]
    c.execute('INSERT INTO task_items(list_id,title,notes,due_date,parent_id,position,created,updated) VALUES (?,?,?,?,?,?,?,?)',(list_id,title,notes[:3000],due_date or None,parent_id or None,pos,now(),now()))
   c.execute('UPDATE task_lists SET updated=? WHERE id=?',(now(),list_id))
  return go('/tasks?list_id='+str(list_id))
 @app.post('/tasks/item/{id}/action')
 def item_action(req:Request,id:int,action:str=Form(...)):
  check(req)
  with db() as c:
   i=valid_item(c,id);l=valid_list(c,i['list_id'])
   if l['archived']:raise HTTPException(409,'Liste ist archiviert')
   if action in ('archive','restore'):
    if action=='archive' and not i['done']:raise HTTPException(409,'Nur erledigte Aufgaben archivieren')
    c.execute('UPDATE task_items SET item_archived=?,updated=? WHERE id=? OR parent_id=?',(int(action=='archive'),now(),id,id))
   elif action=='toggle':
    if i['item_archived']:raise HTTPException(409,'Archivierte Aufgabe zuerst wiederherstellen')
    c.execute('UPDATE task_items SET done=1-done,updated=? WHERE id=?',(now(),id))
   elif action=='delete':c.execute('DELETE FROM task_items WHERE id=?',(id,))
   elif action in ('up','down'):
    # Reorder within the same completion group.
    items=c.execute('SELECT id FROM task_items WHERE list_id=? AND done=? AND COALESCE(parent_id,0)=? AND item_archived=0 ORDER BY position,id',(i['list_id'],i['done'],i['parent_id'] or 0)).fetchall()
    ids=[r['id'] for r in items];idx=ids.index(id);newidx=idx+(-1 if action=='up' else 1)
    if 0<=newidx<len(ids):ids[idx],ids[newidx]=ids[newidx],ids[idx]
    for n,ident in enumerate(ids,1):c.execute('UPDATE task_items SET position=? WHERE id=?',(n,ident))
   else:raise HTTPException(400,'Ungueltige Aktion')
   c.execute('UPDATE task_lists SET updated=? WHERE id=?',(now(),i['list_id']))
  return go('/tasks?list_id='+str(i['list_id'])+('&items_archive=1' if action=='restore' else ''))
