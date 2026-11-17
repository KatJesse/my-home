# Funktionstests Plotten 0.2.6

Automatisch getestet (temporäre SQLite-Datenbank und FastAPI TestClient):
- Neue Lagerposition mit Inventurwert 10
- Auftrag über 3 Stück anlegen: Ist-Bestand bleibt 10
- Geplottet aktivieren: Ist-Bestand bleibt 10
- Gepresst aktivieren: Ist-Bestand wird 7
- Gepresst deaktivieren: Ist-Bestand wird 10
- Gepresst erneut aktivieren und Auftrag löschen: Ist-Bestand wird 10
- Bestellung mit 5 Stück buchen: Ist-Bestand wird 15
- Startimport, Tabellenerstellung und Jinja2-Template-Kompilierung

Nicht getestet: realer Home-Assistant-Docker-Build, Browserdarstellung auf Smartphone, echte Bestandsdaten.
