# Mein Zuhause 0.3.1 – Update und Datenbankmigration

## Änderungen
- Aufgaben: Optionales Fälligkeitsdatum. Anzeige der Resttage in der Aufgabenzeile; überfällige Aufgaben und heute fällige Aufgaben hervorgehoben. Das Datum ist im bestehenden Bearbeitungsmodus änderbar.
- Neue Registerkarte **Essen** (über Einstellungen > Navigation und Layout ausblendbar), mit Wochenplan Montag–Sonntag, beliebig vielen Gerichten je Tag, Rezeptdatenbank, Zutatenlisten, Übernahme einzelner Zutaten auf den Einkaufszettel, Rezeptarchiv und Essensverlauf.
- Gerichte haben Name, Kategorie, Beschreibung, Portionen, Zubereitungszeit, Quelle und Stichwörter. Gerichte sind bearbeitbar, löschbar und archivierbar.
- Essensplan zeigt die aktuelle Woche und bietet Vor-/Zurückblättern. Einträge von gestern bleiben sichtbar; ältere Einträge verschwinden aus der normalen Wochenansicht. Am Wochenwechsel erscheint der Sonntag der Vorwoche als 'Gestern'.
- Der Essensverlauf speichert historische Plan-Einträge für 100 Tage und entfernt ältere Einträge beim Öffnen der Essensseiten. Hinweis: Der Verlauf protokolliert geplante Gerichte, nicht einen separat bestätigten tatsächlichen Verzehr.

## Datenbank
Die bestehende Datei `/data/house.db` wird weiterverwendet. Die Migration erfolgt beim Start automatisch.

`task_items`: neue nullable Spalte `due_date TEXT DEFAULT NULL` (ISO-Format YYYY-MM-DD). Bestehende Aufgaben bleiben unverändert.

Neue Tabellen:
- `food_recipes`: Gerichte und Metadaten, inkl. Archivstatus.
- `food_ingredients`: Zutaten je Gericht mit Fremdschlüssel und Löschweitergabe.
- `food_plan`: Zuordnung Gericht/Datum, gespeicherter Gerichtname für den Verlauf; Fremdschlüssel auf Gericht wird beim Löschen NULL gesetzt.
- Index `idx_food_plan_date`.

Die neue Funktion schreibt Zutatenübernahmen in die bestehende Tabelle `shopping` (nur Bezeichnung und Position).

## Geänderte Dateien gegenüber 0.3.0
- `mein_zuhause/config.yaml`
- `mein_zuhause/app/main.py`
- `mein_zuhause/app/features.py`
- `mein_zuhause/app/tasks.py`
- `mein_zuhause/app/templates/tasks.html`
- `mein_zuhause/app/templates/base.html`
- `mein_zuhause/app/static/style.css`

Neu:
- `mein_zuhause/app/food.py`
- `mein_zuhause/app/templates/food.html`
- `mein_zuhause/app/templates/food_archive.html`
- `UPDATE_0.3.1.md`

## Update
1. Backup der Home-Assistant-App-Daten erstellen.
2. ZIP entpacken, enthaltene Repository-Dateien am bisherigen Ort ersetzen bzw. ergänzen.
3. Mit GitHub Desktop committen und pushen.
4. Repository in Home Assistant aktualisieren und App-Version 0.3.1 installieren (nicht deinstallieren).
5. Browser neu laden, Versionsanzeige `v0.3.1` kontrollieren.

## Prüfumfang
Lokaler Import, Python-Kompilierung, Rendern der Seiten `/tasks`, `/food`, `/food/archive` und `/settings` sowie HTTP-Funktionstests für Gericht, Zutatenübernahme, Planung, Archivierung und Fälligkeitsdatum. Kein Docker-/Raspberry-Pi-Livetest.
