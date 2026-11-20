# Mein Zuhause 0.3.4 – Update von 0.3.3

## Änderungen
- Einkaufszettel: Sortiermodus ohne Checkbox-Spalte, größere Pfeiltasten; abgehakte Einträge werden immer unten angezeigt. Neue anklickbare Spaltenüberschriften Artikel, Geschäft und Menge mit auf-/absteigender Sortierung. Die manuelle Reihenfolge bleibt gespeichert; temporäre Spaltensortierung verändert sie nicht.
- Einkaufsarchiv: archivierte Einkäufe einzeln endgültig löschen (mit Bestätigung).
- Essen: Farbe des Entfernen-Kreuzes und Abstand vor Montag in Einstellungen > Navigation und Layout einstellbar.
- Notizen: To-do-Schaltfläche verwandelt die aktuelle Absatzzeile in eine Checkbox-Zeile, ohne Text in eine neue Zeile zu verschieben. Enter erzeugt nach einer To-do-Zeile einen neuen normalen Absatz.

## Aktualisierte Dateien
- `mein_zuhause/config.yaml`
- `mein_zuhause/app/features.py`
- `mein_zuhause/app/food.py`
- `mein_zuhause/app/templates/shopping.html`
- `mein_zuhause/app/templates/shopping_archive.html`
- `mein_zuhause/app/templates/food.html`
- `mein_zuhause/app/templates/settings.html`
- `mein_zuhause/app/templates/edit.html`
- `mein_zuhause/app/static/style.css`

## Datenbank
Keine neuen Tabellen oder Spalten. Zwei neue Einträge in der vorhandenen `app_settings`-Tabelle: `food_remove_color` (Standard `#8b95a3`) und `food_week_gap` (Standard `26`, Pixel). Werden beim Speichern der Layout-Einstellungen angelegt.

## Installation
Vorher Home-Assistant-Backup erstellen. ZIP entpacken, Dateien in das bestehende GitHub-Repository übernehmen, Commit und Push. In Home Assistant das Repository aktualisieren und Version 0.3.4 installieren, ohne die App zu deinstallieren. Testen: Einkaufszettel (abhaken, sortieren), Einkaufsarchiv löschen, Essensplan-Einstellungen und Notizeditor (To-do mitten in Textzeile und Enter).
