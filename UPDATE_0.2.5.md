# Mein Zuhause 0.2.5 – Update

## Änderungen
- Einkaufszettel: zweiter Abschlussknopf archiviert ausschließlich abgehakte Artikel. Ein aktiver Geschäftsfilter begrenzt beide Abschlussaktionen auf die angezeigten Artikel. Nicht abgehakte Einträge bleiben bei „Gekauftes schließen“ auf dem Einkaufszettel.
- Medienspeicher: Bilder werden erst nach Aufklappen des jeweiligen Eintrags geladen und angezeigt.
- Layout: Die Reihenfolge der kommagetrennten sichtbaren Felder wird bei unterstützten Listenfeldern über CSS `order` angewendet (Desktop und Mobil getrennt). Nicht alle Felder sind in jeder Listenübersicht als eigene Elemente vorhanden; insbesondere `shelf` ist derzeit mit `location` zusammengefasst und lässt sich nicht unabhängig umsortieren.
- Kopfzeile: Abmelden als Navigationsknopf neben den Registerkarten.
- Die Option „Niedrige Bestände auf Einkaufszettel“ ist bereits in Einstellungen → Navigation und Layout vorhanden und steuert die Schaltfläche in Vorräte. Die gewünschte Zuordnung zum Bereich Einkaufszettel ist in dieser Version noch nicht umgesetzt.

## Installation
1. Vollständiges Home-Assistant-Backup mit App-Daten erstellen.
2. Dateien des Pakets im bestehenden GitHub-Repository ersetzen (keinen zusätzlichen Unterordner erzeugen).
3. Commit und Push durchführen.
4. Home-Assistant-App-Repository aktualisieren und Version 0.2.5 installieren; App nicht deinstallieren.
5. Nach dem Start auf `v0.2.5` in der Kopfzeile achten.

## Testempfehlung
Für den Einkaufszettel drei Testartikel anlegen, zwei abhaken, Geschäftsfilter setzen, „Gekauftes schließen und archivieren“ wählen und prüfen, ob nur die beiden abgehakten Artikel des gewählten Geschäfts archiviert wurden.

## Technische Hinweise
Keine Datenbankschemaänderung. Der Build wurde nicht auf einem echten Raspberry Pi ausgeführt. Vor produktiver Nutzung Verhalten und Backups prüfen.
