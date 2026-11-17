# Mein Zuhause 0.2.8 – Update

## Änderungen
- Plotten > Lager: Klickbare Tabellenüberschriften für Hersteller, Textilart, Farbe, Größe, Ist, Vorgemerkt und Verfügbar. Erneuter Klick wechselt zwischen auf- und absteigender Sortierung.
- Plotten > Lager: Neues unabhängiges Folienlager mit Farbe, Größe und Anzahl. Neue Positionen können angelegt, vorhandene über das Stiftsymbol bearbeitet werden.
- „Entnommen (−1)“ reduziert den Folienbestand manuell um genau eine Einheit. Negative Bestände sind erlaubt.
- Folien werden **nicht** automatisch bei Aufträgen, Bestellungen oder Inventur verändert.

## Datenbank
Beim Start wird automatisch die zusätzliche Tabelle angelegt:

```sql
CREATE TABLE IF NOT EXISTS plot_foil_stock (
 id INTEGER PRIMARY KEY,
 color TEXT NOT NULL,
 size TEXT NOT NULL,
 quantity INTEGER NOT NULL DEFAULT 0,
 UNIQUE(color,size)
);
```

Keine vorhandene Tabelle wird verändert. Bestehende Daten bleiben erhalten. Eine Sicherung vor dem Update wird empfohlen.

## Geänderte Dateien gegenüber 0.2.7
- `mein_zuhause/config.yaml`
- `mein_zuhause/app/plotten.py`
- `mein_zuhause/app/templates/plotten.html`
- `mein_zuhause/app/templates/base.html`
- `UPDATE_0.2.8.md` (neu)

## Installation
ZIP entpacken, die Dateien im GitHub-Repository an gleicher Stelle ersetzen, Änderungen committen und pushen. Home-Assistant-Repository aktualisieren, App auf Version 0.2.8 aktualisieren. Nicht deinstallieren.

## Prüfung
Python-Syntaxprüfung und HTTP-Tests mit Testdatenbank für Anlegen, Entnehmen, Bearbeiten sowie Rendering der sortierten Lagerseite bestanden. Kein vollständiger Docker-/Raspberry-Pi-Test.
