import os,tempfile,sys
from pathlib import Path
from fastapi.testclient import TestClient
root=tempfile.mkdtemp();os.environ['HAUS_DATA']=root
sys.path.insert(0,'/mnt/data/work/mein-zuhause-addon/mein_zuhause')
from app.main import app,db,clean_html,make_pdf
client=TestClient(app)
def post(path,data):
 r=client.post(path,data=data,follow_redirects=False);assert r.status_code==303,(path,r.status_code,r.text[:500]);return r
r=client.get('/login');assert r.status_code==200
post('/login',{'username':'admin','password':'strong-password-123'})
for path in ['/','/pantry','/shopping','/storage','/settings','/notes/new']:
 r=client.get(path);assert r.status_code==200,(path,r.status_code,r.text[:400]);print('GET',path,'OK')
post('/categories',{'name':'Test'})
with db() as c:cat=c.execute("SELECT id FROM categories WHERE name='Test'").fetchone()[0]
post('/notes/save',{'title':'Testnotiz','body':'<p><input type="checkbox" checked> Erledigt</p><p>Hallo</p>','category_id':str(cat),'action':'close'})
with db() as c:nid=c.execute("SELECT id FROM notes WHERE title='Testnotiz'").fetchone()[0]
assert client.get('/notes/'+nid).status_code==200
post('/pantry/locations',{'name':'Kueche'})
with db() as c:lid=c.execute("SELECT id FROM pantry_locations").fetchone()[0]
post('/pantry/shelves',{'location_id':str(lid),'name':'Regal 1'})
with db() as c:sid=c.execute("SELECT id FROM pantry_shelves").fetchone()[0]
post('/pantry/categories',{'name':'Konserven'})
post('/pantry/item',{'name':'Tomaten','quantity':'2','minimum':'3','shelf_id':str(sid),'expires':'2026-12-01'})
assert 'Tomaten' in client.get('/pantry').text
post('/pantry/shopping/low',{})
assert 'Tomaten' in client.get('/shopping').text
post('/storage/places',{'name':'Keller'})
with db() as c:pid=c.execute('SELECT id FROM storage_places').fetchone()[0]
post('/storage/box',{'number':'K-001','title':'Weihnachten','place_id':str(pid),'keywords':'Deko'})
assert 'Weihnachten' in client.get('/storage').text
post('/users',{'username':'leser','password':'another-strong-password'})
with db() as c:uid=c.execute("SELECT id FROM users WHERE username='leser'").fetchone()[0]
post('/settings/user/'+str(uid),{'role':'reader'})
client.post('/logout')
post('/login',{'username':'leser','password':'another-strong-password'})
assert client.post('/pantry/locations',data={'name':'Verboten'}).status_code==403
assert client.post('/notes/save',data={'title':'Verboten','category_id':str(cat)}).status_code==403
assert client.get('/pantry').status_code==200
print('ALL TESTS PASSED')
