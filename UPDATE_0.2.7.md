# Mein Zuhause 0.2.7

## Änderungen
- Farbe als eigene Textil-Eigenschaft für Aufträge, Lager, Bestellungen und Inventur.
- Unterregisterkarten Aufträge, Lager, Bestellungen und Inventur.
- Stift in der Lagerzeile zum Bearbeiten von Hersteller, Art, Farbe und Größe.
- Status je Auftrag als Anzahl 0 bis Auftragsmenge statt boolescher Checkbox.
- Lagerentnahme beim Pressen nur für die tatsächlich gepresste Anzahl.
- Gesamtpreis nur je Auftrag, keine übergreifende Summe.

## Datenbankmigration
Automatisch beim Start: `plot_stock.color` und `plot_orders.color` (TEXT, Standard leer). Vorhandene Positionen bleiben mit leerer Farbe erhalten und können über den Stift ergänzt werden. `plot_schema_migrations` merkt die einmalige Umstellung von alten Statuswerten 0/1 auf Stückzahlen; ein vollständig markierter alter Auftrag mit Menge 3 erhält je markiertem Status den Wert 3. `plot_stock` erhält einen eindeutigen Index auf Hersteller/Art/Größe/Farbe. Bestehende Lager- und Bestell-IDs bleiben erhalten. Vor dem Update Backup erstellen.

## Aktualisierte Dateien
- `mein_zuhause/config.yaml`
- `mein_zuhause/app/plotten.py`
- `mein_zuhause/app/templates/plotten.html`
- `mein_zuhause/app/templates/base.html`
- `mein_zuhause/app/static/style.css`
- `UPDATE_0.2.7.md` (neu)

## Installation
Dateien im GitHub-Repository austauschen, committen, pushen, Home-Assistant-Repository aktualisieren, App auf 0.2.7 aktualisieren. Nicht deinstallieren.
