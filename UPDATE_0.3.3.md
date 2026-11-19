# Mein Zuhause 0.3.3 – Update von 0.3.2

Vor dem Update ein Backup der Home-Assistant-App-Daten einschließlich `house.db` erstellen. Die Anwendung nicht deinstallieren. ZIP-Inhalt im GitHub-Repository ersetzen, Commit und Push durchführen, Repository in Home Assistant aktualisieren und Version 0.3.3 installieren.

## Änderungen

- **Essen:** Geplante Gerichte bleiben in vergangenen Wochen sichtbar. Keine automatische 100-Tage-Löschung mehr; manuelles Löschen des Verlaufs im Essensarchiv bleibt möglich.
- **Plotten → Inventur:** Textillagerpositionen einzeln löschen, sofern weder Aufträge noch Einkaufs- oder Bewegungsbuchungen mit ihnen verknüpft sind. Verknüpfte Positionen aus Gründen der Datenintegrität nicht löschen; stattdessen Inventur auf 0.
- **Plotten → Lager:** Folienpositionen einzeln mit Sicherheitsabfrage löschen.
- **Aufgaben:** Erledigte Einzelaufgaben archivieren, archivierte Einzelaufgaben anzeigen, wiederherstellen oder endgültig löschen. Die gesamte Aufgabenliste bleibt dabei aktiv.
- **Notizen:** To-do-Editor ohne künstlichen Leerabsatz und Zero-Width-Zeichen; Checkboxen und Text als Flex-Zeile. Beim Speichern bleiben die sicheren To-do-CSS-Klassen erhalten.

## Datenbankmigration

Beim App-Start wird `task_items` um `item_archived INTEGER NOT NULL DEFAULT 0` ergänzt, falls die Spalte noch nicht existiert. Bestehende Aufgaben bleiben aktiv. Keine weiteren Schemaänderungen. Die Essensplan-Tabelle behält ihre Einträge ohne automatische Löschung.

## Geänderte Dateien gegenüber 0.3.2

- `mein_zuhause/config.yaml`
- `mein_zuhause/app/main.py`
- `mein_zuhause/app/food.py`
- `mein_zuhause/app/tasks.py`
- `mein_zuhause/app/plotten.py`
- `mein_zuhause/app/templates/base.html`
- `mein_zuhause/app/templates/food.html`
- `mein_zuhause/app/templates/tasks.html`
- `mein_zuhause/app/templates/plotten.html`
- `mein_zuhause/app/templates/edit.html`
- `mein_zuhause/app/static/style.css`
- `UPDATE_0.3.3.md` (neu)

## Tests

Python-Kompilierung, Jinja-Template-Parsing, App-Import, API-Test mit Testbenutzer: Aufgaben archivieren und wiederherstellen, vergangenen Essensplan aufrufen, Folienposition löschen. Ein Test auf dem echten Raspberry Pi wurde nicht durchgeführt.
