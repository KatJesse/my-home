# Mein Zuhause – Update 0.3.7

Basis: Version 0.3.6. Vollständiges Add-on, vorhandene Daten bleiben erhalten.

## Aufgaben
- Unteraufgaben sind wie Hauptaufgaben einzeln abhakbar und nach Aufklappen eingerückt sichtbar.
- Verschieben, Bearbeiten, Archivieren und Löschen erscheinen erst nach „Liste bearbeiten“.
- „Erledigte Aufgaben archivieren“ archiviert alle erledigten Hauptaufgaben (einschließlich ihrer Unteraufgaben) sowie einzeln erledigte Unteraufgaben. Im Aufgabenarchiv sind Wiederherstellung und Löschung möglich.
- Gesamte Aufgabenlisten lassen sich wie bisher archivieren und wiederherstellen.

## KFZ
- Neue Registerkarte für mehrere Autos, Anhänger, Motorräder und sonstige Fahrzeuge.
- Stammdaten: Kennzeichen, FIN, Hersteller, Modell, Baujahr, Erstzulassung, Kaufdatum, Kilometerstand, Betriebsstunden, HU/TÜV, Versicherung und Notizen.
- Einträge: Wartung, Reparatur, HU/TÜV, Prüfung, Reifen, Sonstiges mit Datum, Kilometerstand, Betriebsstunden, Fälligkeit (Datum/km), Intervall (Monate/km), Material, Werkstatt, Kosten, Bemerkungen und Erledigtstatus.
- Fahrzeug und Einträge archivieren, wiederherstellen oder endgültig löschen. Dokumente (PDF/Bilder) anhängen und löschen.
- Pro Fahrzeug/Anhänger druckbare PDF-Akte. Zusätzlich enthält die tägliche PDF-Sicherung eine KFZ-Gesamtübersicht sowie Einzel-PDFs aller Fahrzeuge. Die monatlichen PDF-Archive enthalten dieselben Einzel-PDFs.
- Das ZIP-Backup enthält Fahrzeugdaten in SQLite sowie hochgeladene KFZ-Dokumente. Beim Wiederherstellen werden diese Dateien ebenfalls zurückgespielt.

## Installation
1. Vorher eine vollständige Sicherung in Home Assistant und in der App erstellen.
2. ZIP entpacken und Repository-Dateien ersetzen, nicht die Datenbank in /data.
3. GitHub Desktop: Commit und Push.
4. Add-on-Repository aktualisieren und Version 0.3.7 installieren.
5. Unter Einstellungen prüfen, ob KFZ sichtbar ist; ggf. ausgeblendete Registerkarte wieder einblenden.
6. KFZ-Datensatz und Wartung testweise anlegen, Einzel-PDF drucken und unter Einstellungen > Datensicherung eine Sicherung starten. NAS-Ziel und die neuen KFZ-Dateien kontrollieren.

## Änderungen
- Neu: `mein_zuhause/app/kfz.py`, `mein_zuhause/app/templates/kfz.html`.
- Geändert: `tasks.py`, `templates/tasks.html`, `main.py`, `features.py`, `backup.py`, `static/style.css`, `templates/base.html`, `config.yaml`.
- Neue SQLite-Tabellen werden beim Start automatisch angelegt: `kfz_vehicles`, `kfz_events`, `kfz_files`.

## Hinweise
- Die nächtliche Sicherung setzt ein erreichbares NAS und ein laufendes Add-on voraus.
- Kilometer- und Datumsintervalle werden erfasst, aber in dieser Version noch nicht automatisch als nächster Termin fortgeschrieben; Fälligkeiten werden manuell eingetragen.
- Eine vollständige Prüfung auf dem Raspberry Pi und gegen das echte NAS ist noch erforderlich.
