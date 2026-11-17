# Mein Zuhause 0.2.3 – Update und Hinweise

## Installation
1. Vorher ein vollständiges Backup von Home Assistant einschließlich App-Daten erstellen.
2. ZIP entpacken und die Dateien im bestehenden GitHub-Repository ersetzen. Die Verzeichnisstruktur muss erhalten bleiben.
3. Repository im Home-Assistant-App-Store neu laden, dann App auf 0.2.3 aktualisieren (nicht deinstallieren).
4. Unter Einstellungen > Navigation und Layout die Registerkarten und Layoutparameter konfigurieren.
5. Ein Test-Rezept, eine Einkaufsliste und ein Kistenbild prüfen.

## Änderungen
- Keine Seitenüberschriften auf den fünf Hauptseiten; aktive Registerkarte farblich hervorgehoben; Registerkarten umbrechen automatisch.
- Admin kann Registerkarten ausblenden; Direktlinks unter Einstellungen bleiben vorhanden.
- Einkaufszettel: Checkbox links, Informationen daneben, Geschäfte alphabetisch sortiert, Filter bleibt nach Abhaken erhalten.
- Vorräte: mehr Abstand zu Verwaltung, kompaktere Listen und zweifarbige Zeilen; Button für niedrige Bestände ausblendbar.
- To-do: Einfügen ohne Platzhaltertext, Checkbox links neben Text, Durchstreichung nach Abhaken, Zustand beim Speichern gesichert.
- Lager: Suche und Anlegen nebeneinander (wenn Bildschirmbreite reicht).
- Medienübersicht: Administratoren sehen Notizbilder und Kistenbilder mit Dateidatum; unwiderrufliches Löschen möglich.
- Admin-Layoutoptionen getrennt nach Desktop und Mobilgerät: Schriftgröße, Zeilen- und Informationsabstände, Abstand zu Menüs, Farben, Spalten, sichtbare und fett markierte Felder.

## Einschränkungen
- Bei bestehenden Bilddateien entspricht das angezeigte Datum dem Änderungszeitpunkt der Datei; das ursprüngliche Upload-Datum wurde bisher nicht gesondert gespeichert.
- Die Spaltenzahl beeinflusst die Karten-/Listenaufteilung; komplexe Tabellenformate werden nicht neu strukturiert.
- Feldsichtbarkeit und Fettdruck sind für die vordefinierten Listenfelder umgesetzt, nicht für sämtliche Elemente der Detailansichten.
- Bei mehrspaltigen Listen auf sehr schmalen Displays können Inhalte eng werden.
- Die automatische PDF-Erstellung ist von den Layout-Einstellungen der Weboberfläche unabhängig.
- Die App ist nicht auf einem realen Raspberry Pi getestet; Funktionstests sind lokal ausgeführt.
- Medien löschen kann PDFs mit eingebetteten Bildern verändern. Unbedingt vorher sichern.
