# Mein Zuhause 0.2.0 – Installation des Updates

1. Vorher unter **Einstellungen > System > Backups** ein vollständiges Home-Assistant-Backup einschließlich App-Daten anlegen. Zusätzlich wichtige Dateien der FRITZ!NAS sichern. Nicht deinstallieren und nicht die App-Daten löschen.
2. Die Dateien des ZIPs in das **bestehende** GitHub-Repository hochladen und die bisherigen Dateien ersetzen. Ordner `mein_zuhause` muss direkt im Repository-Hauptverzeichnis liegen.
3. Prüfen: `mein_zuhause/config.yaml` enthält `version: "0.2.0"`.
4. Home Assistant > Einstellungen > Apps > App-Store > Drei-Punkte-Menü > Nach Updates suchen / Neu laden. Dann App **Mein Zuhause** auf 0.2.0 aktualisieren.
5. Die bisherige Konfiguration, insbesondere `pdf_directory`, **unverändert** lassen. Nicht neu installieren, da sonst je nach Aktion App-Daten verloren gehen könnten.
6. App starten. In **Protokoll** auf Fehler prüfen. Startseite, altes Rezept und PDF-Export prüfen.
7. Die Datenbank wird beim ersten Start um Tabellen ergänzt. Eine einmalige Kopie `house-before-0.2.0.db` wird im persistenten App-Datenordner angelegt. Das ist kein Ersatz für ein vollständiges Home-Assistant-Backup.

## Neue Menüs
Notizen · Vorräte · Einkaufszettel · Lager · Einstellungen.

## Funktionen
- Notizen: Filter nach Kategorie, Status und Sortierung; individuelle Kategorie-Sichtbarkeit; Checklisten mit durchgestrichenen erledigten Absätzen; Speichern oder Speichern und schließen; Bild-Dateinamen werden nicht mehr in PDFs gedruckt.
- Vorräte: Lagerplätze, Regalfächer, Kategorien, Bestand, Einheit, Mindestmenge, Ablauf- und Einfrierdatum, geöffnet, entnommene Menge, Barcode und Notizen. Suche und Ablaufwarnungen.
- Einkaufszettel: manuelle Einträge, Übernahme aus Vorräten, nach Geschäft filtern, per Pfeilen sortieren, abhaken.
- Lager: Lagerorte, nummerierte Kisten/Gegenstände, Stichworte, Notizen, Freitext-Metadaten, ein Bild pro Eintrag.
- Einstellungen: Benutzer anlegen und löschen, Rolle ändern (Admin, Schreiber, Leser), Kategorie-Sichtbarkeit, Ablauf-Vorwarnzeit, lokale Datenträgerbelegung.

## Bekannte Einschränkungen
- Die Speicherplatzanzeige misst das Dateisystem der lokalen App-Daten, nicht zwingend die FRITZ!NAS-SSD.
- Die Lagerverwaltung unterstützt zunächst **ein Bild je Kiste**, nicht beliebig viele Bilder oder Anhänge.
- Die Einkaufszettel-Reihenfolge wird mit Auf/Ab-Schaltflächen geändert, nicht per Drag-and-drop.
- Mengen werden nicht automatisch beim Abhaken des Einkaufszettels in die Vorratsdatenbank gebucht.
- Die `entnommene Menge` ist ein Informationsfeld; die Bestandsmenge wird manuell gepflegt.
- HTML-Editor-Checklisten werden im PDF als `[x]` und `[ ]` ausgegeben; vollständige CSS-Durchstreichung im PDF ist noch nicht garantiert.
- Es gibt noch keine automatisierte Hintergrund-Wiederholung fehlgeschlagener PDF-Exporte.
- Die Suche in Vorräten/Lager nutzt Textfilter, Notizen die vorhandene Volltextsuche inklusive OCR.
- Nicht in einer öffentlich erreichbaren Internet-URL ohne zusätzliche Absicherung betreiben. VPN-Zugriff empfohlen.

## Testplan
1. Bestehendes Rezept öffnen, ändern und speichern; prüfen, dass es weiterhin auf der FRITZ!NAS erscheint.
2. Testnotiz mit Checkliste erstellen, abhaken und erneut öffnen.
3. Notizkategorie ausblenden und wieder einblenden.
4. Benutzer `Leser` anlegen und Schreibversuch prüfen.
5. Lagerplatz/Regalfach/Kategorie anlegen, Lebensmittel mit Ablaufdatum speichern, Warnfilter testen.
6. Artikel auf Einkaufszettel übertragen, Geschäft zuordnen und Reihenfolge ändern.
7. Lagerort und Kiste anlegen, Foto hochladen, über Stichwort suchen.

## Erweiterung 0.2.1 – Speicherziel in Einstellungen

Unter Einstellungen > PDF-Speicherziel können Administratoren zwischen dem bereits eingerichteten Home-Assistant-Netzwerkspeicher (empfohlen) und direktem SMB-Zugriff wählen. Bei direktem SMB-Zugriff sind Server, Freigabe, Unterordner, Benutzername und Passwort einstellbar. Ein leeres Passwortfeld behält das zuvor gespeicherte Passwort. Der lokale PDF-Export bleibt bestehen; nach erfolgreichem PDF-Export wird die Datei zusätzlich auf SMB übertragen. Der SMB-Modus benötigt `samba-client` im Container und setzt die SMB-Version 3 ein.

Beispiel FRITZ!Box: Server `192.168.178.1`, Freigabe `FRITZ.NAS`, Unterordner `INTENSO/MeinZuhause`. Der genaue Unterordner hängt von der Freigabe ab. Es dürfen keine vollständigen `smb://`-URLs in das Serverfeld eingetragen werden.

Sicherheit: Die SMB-Zugangsdaten liegen in der lokalen SQLite-App-Datenbank und sind nicht zusätzlich verschlüsselt. Einen dedizierten FRITZ!Box-Benutzer mit begrenzten NAS-Rechten nutzen; App-Backups schützen. Das Passwort wird im Formular nicht wieder angezeigt. Der direkte SMB-Modus unterstützt noch keinen Verbindungstest per Knopf und entfernt bei Archivierung keine bereits auf das NAS übertragenen PDFs. Die bereits eingerichtete HA-Netzwerkfreigabe ist deshalb vorzuziehen.

Update: GitHub-Dateien einschließlich `mein_zuhause/app/main.py`, `features.py`, `templates/settings.html`, `Dockerfile`, `config.yaml` ersetzen; im App-Store aktualisieren, nicht deinstallieren. Vorher Backup erstellen. Version 0.2.1.
