# Update Mein Zuhause 0.2.6

## Installation
1. Home-Assistant-Backup der bestehenden App-Daten erstellen.
2. Dateien aus dem ZIP **an den gleichen Pfaden** im bestehenden GitHub-Repository ersetzen/hinzufügen (keine zweite Repository-Ebene).
3. Commit und Push durchführen; Repository in Home Assistant neu laden; App auf 0.2.6 aktualisieren, **nicht deinstallieren**.
4. Nach Anmeldung die Registerkarte **Plotten** und die Anzeige `v0.2.6` prüfen.

## Geänderte Dateien (gegenüber 0.2.5)
- `mein_zuhause/config.yaml` (Version)
- `mein_zuhause/app/main.py` (Navigation und Registrierung)
- `mein_zuhause/app/templates/base.html` (Versionsanzeige/Cache)
- `mein_zuhause/app/static/style.css` (Darstellung)

## Neue Dateien
- `mein_zuhause/app/plotten.py` (Datenmodell, Buchungslogik, Routen)
- `mein_zuhause/app/templates/plotten.html` (Oberfläche)
- `UPDATE_0.2.6.md` (diese Anleitung)

## Datenbankänderungen
Beim Start werden in der bestehenden `/data`-Datenbank `house.db` automatisch fünf neue Tabellen mittels `CREATE TABLE IF NOT EXISTS` angelegt. Bestehende Tabellen werden nicht verändert:

- `plot_stock`: Hersteller, Textilart, freie Größe, Ist-Bestand (darf negativ sein), eindeutige Kombination der drei Merkmale.
- `plot_orders`: Aufträge mit Name, Menge, Einzelpreis in **Cent**, fünf Bearbeitungskennzeichen, Archivstatus und Zeitstempeln.
- `plot_purchases`: Bestellkopf mit manuellem Bestelldatum.
- `plot_purchase_items`: einzelne Bestellpositionen mit Menge und Einkaufspreis in Cent.
- `plot_movements`: unveränderliche Buchungszeilen mit Bestandsdelta, Buchungsgrund, optionaler Referenz und Zeitstempel.

Keine Migration bestehender Tabellen nötig. Beim Start bleiben alle bisherigen Notizen, Vorräte und Einkaufszettel erhalten.

## Lagerlogik
- Ein offener Auftrag reserviert seine Menge. Reserviert wird **berechnet**, nicht als separate Bestandsbuchung gespeichert.
- **Erst „Gepresst“** bucht die Auftragsmenge aus dem Ist-Bestand aus. „Geplottet“ und „Entkettet“ ändern den Bestand nicht.
- Zurücksetzen von „Gepresst“ bucht zurück und reserviert wieder.
- Bearbeitung eines gepressten Auftrags bucht die alte Entnahme zurück und die neue Entnahme; Löschen bucht eine Entnahme ebenfalls zurück.
- Archivieren ist nur möglich, wenn alle fünf Statusfelder gesetzt sind; archivierte Aufträge bleiben in der Bestandshistorie berücksichtigt.
- Bestellung buchen erhöht den Bestand sofort. Inventur setzt den Ist-Bestand auf die gezählte Zahl und protokolliert die Differenz.

**Wichtig:** Eine Bestellung wird derzeit direkt als Wareneingang behandelt, nicht als offene Lieferantenbestellung. Bereits gebuchte Bestellungen können nicht nachträglich bearbeitet werden; eine Korrektur erfolgt über Inventur. Die Anzeige ist auf 30 jüngste Bestellungen begrenzt, die Datenbank bewahrt alle auf.
