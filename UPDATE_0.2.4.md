# Mein Zuhause 0.2.4 – Diagnose- und Anzeigeupdate

- Die Kopfzeile zeigt nach Anmeldung rechts `v0.2.4`. Damit ist sichtbar, ob der neue HTML-Stand ausgeliefert wird.
- Das Stylesheet verwendet einen Versions-/Hash-Parameter, um alte Browser-Caches zu umgehen.
- HTML-Antworten werden mit `Cache-Control: no-store` ausgeliefert.
- Die Startseite wurde anhand der Jinja2-Vorlagen mit Testdaten lokal gerendert; ein echter HA-OS-Test steht aus.

## Installation
1. Backup der App-Daten erstellen.
2. Alle Dateien aus `mein_zuhause/` im gleichnamigen Ordner des GitHub-Repositories ersetzen; `repository.yaml` bleibt im Repository-Stamm.
3. Commit und Push, dann im HA-App-Store Repository neu laden und App auf 0.2.4 aktualisieren. Nicht deinstallieren.
4. Nach Login muss in der Kopfzeile `v0.2.4` stehen. Fehlt die Markierung, läuft nicht die neue HTML-Vorlage.
5. Nach Update ggf. Strg+F5. Wenn weiterhin alt: Build-Protokoll und GitHub-Dateipfade prüfen.

## Erwartete Startseite
Kopfzeile mit fünf Registerkarten, aktiver Tab Notizen hervorgehoben; rechts Benutzername, Abmelden und Versionsmarker. Im Inhalt ein Button `+ Neuer Eintrag`, ein einklappbarer Bereich `Suche und Filter`, Anzahl der Einträge und Karten der vorhandenen Notizen.
