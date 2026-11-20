"""Weekly meal planning, recipes, ingredients, shopping transfer and rolling history."""
from datetime import date,timedelta
from fastapi import Request,Form,HTTPException
from fastapi.responses import HTMLResponse

WEEKDAYS=('Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag')

def install_food(app,db,require,writer,safe_post,render,go,now):
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS food_recipes(id INTEGER PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL DEFAULT '',description TEXT NOT NULL DEFAULT '',servings INTEGER,minutes INTEGER,source TEXT NOT NULL DEFAULT '',tags TEXT NOT NULL DEFAULT '',archived INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS food_ingredients(id INTEGER PRIMARY KEY,recipe_id INTEGER NOT NULL REFERENCES food_recipes(id) ON DELETE CASCADE,name TEXT NOT NULL,position INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS food_plan(id INTEGER PRIMARY KEY,recipe_id INTEGER REFERENCES food_recipes(id) ON DELETE SET NULL,recipe_title TEXT NOT NULL,meal_date TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(recipe_id,meal_date));
  CREATE INDEX IF NOT EXISTS idx_food_plan_date ON food_plan(meal_date);
  ''')
 def check(req):writer(req);safe_post(req)
 def cleanup(c):
  # History is retained for at least three calendar months (100 days).
  cutoff=(date.today()-timedelta(days=100)).isoformat()
  c.execute('DELETE FROM food_plan WHERE meal_date<?',(cutoff,))
 def recipe(c,rid):
  r=c.execute('SELECT * FROM food_recipes WHERE id=?',(rid,)).fetchone()
  if not r:raise HTTPException(404,'Gericht nicht gefunden')
  return r
 def week_start(offset):
  if abs(offset)>52:raise HTTPException(400,'Woche außerhalb des Bereichs')
  d=date.today()
  return d-timedelta(days=d.weekday())+timedelta(weeks=offset)
 @app.get('/food',response_class=HTMLResponse)
 def food(req:Request,week:int=0):
  require(req);monday=week_start(week);sunday=monday+timedelta(days=6)
  with db() as c:
   recipes=c.execute('SELECT * FROM food_recipes WHERE archived=0 ORDER BY title COLLATE NOCASE,id').fetchall()
   ingredients={r['id']:[dict(x) for x in c.execute('SELECT id,name FROM food_ingredients WHERE recipe_id=? ORDER BY position,id',(r['id'],))] for r in recipes}
   food_opts={r['key']:r['value'] for r in c.execute("SELECT key,value FROM app_settings WHERE key IN ('food_remove_color','food_week_gap')")}
   plan=c.execute('SELECT * FROM food_plan WHERE meal_date BETWEEN ? AND ? ORDER BY meal_date,id',(monday.isoformat(),sunday.isoformat())).fetchall()
  days=[{'date':(monday+timedelta(days=i)).isoformat(),'label':WEEKDAYS[i],'items':[p for p in plan if p['meal_date']==(monday+timedelta(days=i)).isoformat()]} for i in range(7)]
  return render(req,'food.html',days=days,recipes=recipes,ingredients=ingredients,week=week,week_start=monday,week_end=sunday,yesterday_items=[],today=date.today().isoformat(),food_remove_color=food_opts.get('food_remove_color','#8b95a3'),food_week_gap=food_opts.get('food_week_gap','26'))
 @app.post('/food/recipe')
 def save_recipe(req:Request,id:int=Form(0),title:str=Form(...),category:str=Form(''),description:str=Form(''),servings:str=Form(''),minutes:str=Form(''),source:str=Form(''),tags:str=Form(''),ingredients:str=Form('')):
  check(req);title=title.strip()[:160]
  if not title:raise HTTPException(400,'Gerichtname erforderlich')
  def positive(value):
   if not value.strip():return None
   try:n=int(value)
   except ValueError:raise HTTPException(400,'Ungültige Zahl')
   if not 0<n<=10000:raise HTTPException(400,'Ungültige Zahl')
   return n
  servings=positive(servings);minutes=positive(minutes)
  names=[line.strip()[:160] for line in ingredients.splitlines() if line.strip()][:150]
  with db() as c:
   if id:
    recipe(c,id)
    c.execute('UPDATE food_recipes SET title=?,category=?,description=?,servings=?,minutes=?,source=?,tags=?,updated=? WHERE id=?',(title,category[:100],description[:5000],servings,minutes,source[:300],tags[:300],now(),id))
    c.execute('DELETE FROM food_ingredients WHERE recipe_id=?',(id,))
   else:
    id=c.execute('INSERT INTO food_recipes(title,category,description,servings,minutes,source,tags,created,updated) VALUES (?,?,?,?,?,?,?,?,?)',(title,category[:100],description[:5000],servings,minutes,source[:300],tags[:300],now(),now())).lastrowid
   c.executemany('INSERT INTO food_ingredients(recipe_id,name,position) VALUES (?,?,?)',[(id,name,i) for i,name in enumerate(names)])
  return go('/food#recipes')
 @app.post('/food/recipe/{id}/action')
 def recipe_action(req:Request,id:int,action:str=Form(...)):
  check(req)
  with db() as c:
   recipe(c,id)
   if action=='archive':c.execute('UPDATE food_recipes SET archived=1 WHERE id=?',(id,))
   elif action=='delete':
    # Historical entries keep a snapshot of the recipe title.
    c.execute('DELETE FROM food_recipes WHERE id=?',(id,))
   elif action=='restore':c.execute('UPDATE food_recipes SET archived=0 WHERE id=?',(id,))
   else:raise HTTPException(400,'Ungültige Aktion')
  return go('/food#recipes')
 @app.post('/food/plan')
 def plan(req:Request,recipe_id:int=Form(...),meal_date:str=Form(...),week:int=Form(0)):
  check(req)
  try:d=date.fromisoformat(meal_date)
  except ValueError:raise HTTPException(400,'Ungültiges Datum')
  monday=week_start(week)
  if not monday<=d<=monday+timedelta(days=6):raise HTTPException(400,'Datum liegt außerhalb der angezeigten Woche')
  with db() as c:
   r=recipe(c,recipe_id)
   if r['archived']:raise HTTPException(409,'Gericht ist archiviert')
   c.execute('INSERT OR IGNORE INTO food_plan(recipe_id,recipe_title,meal_date,created) VALUES (?,?,?,?)',(recipe_id,r['title'],d.isoformat(),now()))
  return go('/food?week='+str(week))
 @app.post('/food/plan/{id}/delete')
 def plan_delete(req:Request,id:int,week:int=Form(0)):
  check(req)
  with db() as c:c.execute('DELETE FROM food_plan WHERE id=?',(id,))
  return go('/food?week='+str(week))
 @app.post('/food/ingredient/{id}/shopping')
 def ingredient_shopping(req:Request,id:int):
  check(req)
  with db() as c:
   r=c.execute('SELECT name FROM food_ingredients WHERE id=?',(id,)).fetchone()
   if not r:raise HTTPException(404,'Zutat nicht gefunden')
   c.execute('INSERT INTO shopping(name,position) VALUES (?,(SELECT COALESCE(MAX(position),0)+1 FROM shopping))',(r['name'],))
  return go('/food#recipes')
 @app.get('/food/archive',response_class=HTMLResponse)
 def archive(req:Request):
  require(req)
  with db() as c:
   history=c.execute('SELECT * FROM food_plan WHERE meal_date<=? ORDER BY meal_date DESC,id DESC',(date.today().isoformat(),)).fetchall()
   recipes=c.execute('SELECT * FROM food_recipes WHERE archived=1 ORDER BY title COLLATE NOCASE').fetchall()
  return render(req,'food_archive.html',history=history,recipes=recipes)
 @app.post('/food/archive/clear')
 def archive_clear(req:Request,action:str=Form(...)):
  check(req)
  with db() as c:
   if action=='history':c.execute('DELETE FROM food_plan WHERE meal_date<=?',(date.today().isoformat(),))
   elif action=='recipes':c.execute('DELETE FROM food_recipes WHERE archived=1')
   else:raise HTTPException(400,'Ungültige Aktion')
  return go('/food/archive')
