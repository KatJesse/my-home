# Update 0.3.2

## Änderungen
- Aufgaben: Sortiermodus unten mit Pfeilen, Speichern und Abbrechen. Die Sortierung wird pro Liste gespeichert. Offene Aufgaben stehen weiterhin vor erledigten.
- Notizen: Eintragsanzahl und Kategorienhinweis unter der Liste.
- Abmelden: ausschließlich oben unter Einstellungen, kompaktere Kopfzeile.
- Einstellungen: Administrator kann Bezeichnungen für Registerkarten, Überschriften und Schaltflächen zentral ändern und zurücksetzen. Erfasst sind statische UI-Texte aus den Vorlagen; dynamisch erzeugte Texte und Inhalte werden nicht umbenannt.

## Datenbank
Keine neue Tabelle. Neue optionale app_settings-Einträge `label_<Standardtext>` für Bezeichnungen. Aufgabenreihenfolge nutzt `task_items.position`.

## Aktualisierte Dateien
- mein_zuhause/config.yaml
- mein_zuhause/app/main.py
- mein_zuhause/app/tasks.py
- mein_zuhause/app/templates/base.html
- mein_zuhause/app/templates/home.html
- mein_zuhause/app/templates/tasks.html
- mein_zuhause/app/templates/settings.html
- mein_zuhause/app/static/style.css

## Neue Datei
- mein_zuhause/app/static/ui_labels.js

## Installation
Backup der App-Daten erstellen, ZIP entpacken, Projektdateien im GitHub-Repository ersetzen und neue Datei ergänzen. Commit und Push, danach Home-Assistant-Repository aktualisieren und Version 0.3.2 installieren. App nicht deinstallieren.
