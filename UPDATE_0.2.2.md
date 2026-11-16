# Mein Zuhause 0.2.2 – kompakte Listen und Einkaufsarchiv

## Änderungen
- Logo/Schriftzug im Kopf entfernt; kleinere, voneinander abgesetzte Navigationsschaltflächen.
- Filter für Notizen, Vorräte, Lager und Einkaufszettel einklappbar.
- Vorräte und Lager: eine kompakte Übersichtszeile je Eintrag; Detaildaten und Aktionen erst nach Aufklappen.
- Einkaufszettel: einzeilige Artikel mit Checkbox, Bezeichnung und Menge; weitere Felder aufklappbar. Erledigte Artikel werden nach unten sortiert.
- Einkauf abschließen: archiviert den aktuellen Einkaufszettel oder das ausgewählte Geschäft mit Datum, Geschäft und Artikeln. Archivierte Einkäufe können wiederhergestellt werden.

## Daten und Migration
Beim Start werden die neuen Tabellen `shopping_archives` und `shopping_archive_items` mit `CREATE TABLE IF NOT EXISTS` angelegt. Bestehende Notizen, Einkäufe und NAS-Konfiguration bleiben unverändert. Vor der Aktualisierung ein vollständiges Home-Assistant-Backup einschließlich App-Daten erstellen.

## Update
1. ZIP entpacken und Dateien im vorhandenen GitHub-Repository mit identischer Ordnerstruktur aktualisieren.
2. Prüfen, dass `mein_zuhause/config.yaml` die Version `0.2.2` enthält.
3. Home Assistant: Einstellungen > Apps > App-Store > Menü > Nach Updates suchen.
4. App auf 0.2.2 aktualisieren (nicht deinstallieren).
5. Vorräte/Lager aufklappen, Einkaufsartikel abhaken, Einkauf schließen und im Archiv wiederherstellen testen.

## Einschränkungen
- Beim Schließen werden alle Artikel des aktuellen Einkaufszettels bzw. des ausgewählten Geschäfts archiviert, auch nicht abgehakte. Die Auswahl wird im Bestätigungsdialog angezeigt.
- Wiederherstellen führt die archivierten Artikel zum bestehenden Einkaufszettel hinzu; mögliche Duplikate werden nicht automatisch entfernt.
- Für komplexe Einkaufslisten ist noch keine getrennte Verwaltung gleichzeitig aktiver Einkaufsrunden implementiert.
- Python-Syntaxprüfung durchgeführt; noch kein echter Test auf Raspberry Pi / Home Assistant OS.
