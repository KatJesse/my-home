# Mein Zuhause – Update 0.3.5

## Neu
- Einkaufszettel: eigener, zweispaltiger Sortiermodus mit großen Pfeilen; Checkboxen sind im Sortiermodus vollständig ausgeblendet. Die normale Ansicht bleibt unverändert.
- Aufgaben: beliebig viele Unteraufgaben mit Fälligkeitsdatum je Hauptaufgabe; erledigte Unteraufgaben erscheinen innerhalb ihrer Hauptaufgabe unten. Bearbeiten, Archivieren, Wiederherstellen und Löschen werden unterstützt.
- Einstellungen > Datensicherung: vollständiges ZIP-Backup (SQLite-Datenbank und hochgeladene Dateien), manuelle Erstellung, ZIP-Download und Wiederherstellung aus einer hochgeladenen ZIP-Datei oder einer lokal vorhandenen Sicherung.
- Lesbare PDF-Exporte für alle Bereiche einschließlich archivierter Inhalte, mit einer zusätzlichen Datei „Weitere Daten“ für Tabellen, die keiner Registerkarte eindeutig zugeordnet sind.
- Automatische tägliche Sicherung ab 02:00 Uhr (Zeitzone Europe/Berlin). Ein Monatsarchiv wird am letzten Kalendertag um 23:59 Uhr angelegt, sofern die App dann läuft.
- Sieben lokale tägliche ZIP-Sicherungen werden aufbewahrt; die täglichen ZIP-Dateien auf dem NAS verwenden Tagesnamen, ältere werden entfernt. Monatsarchive bleiben dauerhaft bestehen.

## NAS und Sicherungsort
- Im Modus SMB: unter dem in den Einstellungen angegebenen SMB-Unterordner `MeinZuhause-Sicherungen/PDFs/Aktuell`, `PDFs/Monatsarchive`, `Backup/Aktuell`, `Backup/Monatsarchive`.
- Im lokalen Modus: unter dem konfigurierten `/share/...`-PDF-Verzeichnis im Unterordner `MeinZuhause-Sicherungen`. Wichtig: `/share` ist nicht automatisch dein NAS. Stelle sicher, dass der Ordner auf dein NAS gesichert oder eingebunden ist. Alternativ den vorhandenen SMB-Modus konfigurieren.
- Ein NAS-Ausfall verhindert die erfolgreiche Veröffentlichung und wird als Fehler unter Datensicherung angezeigt. Lokal erzeugte Dateien bleiben erhalten.
- Für die Wiederherstellung einer Sicherung, die nur auf dem NAS liegt, die ZIP-Datei herunterladen und über „ZIP-Datei vom Computer“ einlesen. Die App kann lokal vorhandene Sicherungen direkt auswählen.

## Wiederherstellung
1. Backup-ZIP auswählen und `WIEDERHERSTELLEN` eingeben.
2. Die App legt vor dem Ersetzen ein lokales Rettungsbackup an und prüft ZIP und SQLite-Datenbank.
3. Danach die App neu starten. Bestehende Daten und Uploads werden durch den Backup-Stand ersetzt.
4. Ein vollständiges Home-Assistant-Systembackup ist zusätzlich empfohlen.

## Datenbank
- Die Tabelle `task_items` erhält bei Bedarf die Spalte `parent_id`. Bestehende Aufgaben bleiben Hauptaufgaben.
- Backups werden mit SQLite-Online-Backup erstellt (konsistenter Snapshot).

## Technische Einschränkungen
- Die automatische Sicherung läuft nur, während das Add-on gestartet ist. Nach einer Downtime wird die tägliche Sicherung nachgeholt, sobald die App nach 02:00 Uhr läuft. Das Monatsarchiv benötigt den laufenden Dienst am Monatsende.
- PDF-Dateien sind menschenlesbare Notfallkopien; Bilder und sonstige Anhänge liegen vollständig im ZIP-Backup, nicht als vollständige eingebettete PDF-Anhänge.
- Ein Wiederherstellungsprozess kann bestehende Browser-Sitzungen ungültig machen. Nach dem Restore die App neu starten.

## Geänderte Dateien
- `mein_zuhause/config.yaml`
- `mein_zuhause/app/main.py`
- `mein_zuhause/app/tasks.py`
- `mein_zuhause/app/backup.py` (neu)
- `mein_zuhause/app/templates/tasks.html`
- `mein_zuhause/app/templates/backup.html` (neu)
- `mein_zuhause/app/templates/settings.html`
- `mein_zuhause/app/templates/base.html`
- `mein_zuhause/app/static/style.css`

## Installation
ZIP entpacken, Dateien im GitHub-Repository ersetzen, Commit und Push durchführen, dann das Home-Assistant-Repository aktualisieren und Version 0.3.5 installieren. Vorher ein bestehendes Backup sichern.
