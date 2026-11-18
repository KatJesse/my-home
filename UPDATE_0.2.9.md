# Mein Zuhause 0.2.9 – Update von 0.2.8

Vor dem Update ein Backup der Home-Assistant-App-Daten erstellen. ZIP entpacken, Dateien in das bestehende GitHub-Repository an derselben Position kopieren, Commit und Push ausführen, Repository in Home Assistant aktualisieren und 0.2.9 installieren. Die App nicht deinstallieren.

## Neue Funktionen

- Plotten → Aufträge: Unter der Auftragsliste die Summe der Auftragsgesamtpreise (Anzahl × Einzelpreis) sowie fünf offene Stückzahlsummen für die aktuell angezeigten Aufträge. Ausblendbar über Einstellungen → Navigation und Layout → „Zusammenfassung unter Plotten → Aufträge anzeigen“.
- Einkaufszettel: Filter „Ohne Geschäft“; am Listenende „Sortieren aktivieren“, dann Artikel über Pfeile hoch/runter bewegen und „Reihenfolge speichern“. Die Reihenfolge wird serverseitig gespeichert. Bei gefilterten Listen bleiben ausgeblendete Artikel an ihren bisherigen Positionen.
- Aufgaben: Eigene Hauptregisterkarte, in Einstellungen ausblendbar. Beliebig viele Aufgabenlisten mit jeweils eigener Unteransicht; Punkte hinzufügen, bearbeiten, abhaken, verschieben und löschen; erledigte Punkte automatisch unten. Listen bearbeiten, archivieren, wiederherstellen und löschen.

## Datenbankmigration

Beim Start automatisch und ohne Änderung bestehender Tabellen:

```sql
CREATE TABLE IF NOT EXISTS task_lists (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  archived INTEGER NOT NULL DEFAULT 0,
  created TEXT NOT NULL,
  updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS task_items (
  id INTEGER PRIMARY KEY,
  list_id INTEGER NOT NULL REFERENCES task_lists(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  done INTEGER NOT NULL DEFAULT 0,
  position INTEGER NOT NULL DEFAULT 0,
  created TEXT NOT NULL,
  updated TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_task_items_list ON task_items(list_id,done,position,id);
```

Neue Konfigurationsschlüssel in der vorhandenen `app_settings`-Tabelle: `hide_tab_tasks`, `show_plot_summary` (Standard: sichtbar). Die Einkaufszettel-Reihenfolge nutzt die bereits vorhandene Spalte `shopping.position`.

## Geänderte Dateien gegenüber 0.2.8

- `mein_zuhause/config.yaml`
- `mein_zuhause/app/main.py`
- `mein_zuhause/app/features.py`
- `mein_zuhause/app/plotten.py`
- `mein_zuhause/app/templates/base.html`
- `mein_zuhause/app/templates/settings.html`
- `mein_zuhause/app/templates/shopping.html`
- `mein_zuhause/app/templates/plotten.html`
- `mein_zuhause/app/static/style.css`

Neu:
- `mein_zuhause/app/tasks.py`
- `mein_zuhause/app/templates/tasks.html`
- `UPDATE_0.2.9.md`

## Tests

Syntaxprüfung aller Python-Module und Jinja-Templates. FastAPI-TestClient mit Testdatenbank: Aufgabenlisten anlegen/archivieren/wiederherstellen, Aufgaben hinzufügen und abhaken (Erledigte unten), Einkaufsfilter „Ohne Geschäft“, manuelle Sortierreihenfolge, Einstellungsänderung und Seitenrendering. Ein Docker-Build und die Installation auf dem Raspberry Pi wurden nicht durchgeführt.
