# Mein Zuhause – Installationsanleitung (Home Assistant OS, Raspberry Pi 4)

## 0. Was ist enthalten?

Eigenes Home-Assistant-App-Repository (früher Add-on-Repository), Weboberfläche auf Port 8099, Benutzerkonten, Rich-Text-Notizen, Kategorien, Anhänge, OCR, Suche, Archiv/Papierkorb, PDF-Export. **HACS wird nicht benötigt.** Version 0.1.0 ist ein technischer Prototyp, nicht sicherheitsgeprüft. Kein direkter Internetzugang, nur Heimnetz/VPN. Vor dem Einsatz mit sensiblen Unterlagen die Einschränkungen in `NACHBAU_SPEZIFIKATION.txt` lesen.

## 1. Voraussetzungen

- Raspberry Pi 4 mit Home Assistant OS und SSD
- Zugriff als Home-Assistant-Administrator
- FRITZ!Box-NAS mit SMB-Freigabe (optional für erste Tests)
- Für Fernzugriff ein bereits eingerichtetes VPN, etwa WireGuard auf der FRITZ!Box
- Rechner mit GitHub-Zugang oder ein lokaler Git-Server, der von Home Assistant aus erreichbar ist

## 2. Repository veröffentlichen

1. ZIP `mein-zuhause-addon.zip` entpacken.
2. Bei GitHub ein **öffentliches** Repository `mein-zuhause-addon` erstellen. Das Repository enthält **nur Programmcode, keine persönlichen Daten oder Passwörter**.
3. Alle Dateien und Ordner aus dem entpackten Verzeichnis ins Stammverzeichnis des Repositories hochladen. Wichtig: `mein_zuhause/config.yaml` muss direkt unter dem Repository-Stamm liegen.
4. In `repository.yaml` und `mein_zuhause/config.yaml` die Beispiel-URL `https://github.com/DEIN-NAME/mein-zuhause-addon` durch die echte URL ersetzen.
5. Änderungen committen. Alternativ kann ein lokal erreichbarer HTTP(S)-Git-Server verwendet werden.

## 3. App in Home Assistant installieren

1. Home Assistant öffnen.
2. **Einstellungen → Apps** (in älteren Versionen **Add-ons**) öffnen.
3. Den **App-Store** öffnen; über das Drei-Punkte-Menü **Repositories** auswählen.
4. URL deines GitHub-Repositories eintragen und hinzufügen.
5. App-Store neu laden, **Mein Zuhause** auswählen und **Installieren**.
6. Der erste Build kann auf dem Pi 4 einige Minuten dauern, weil Python-Bibliotheken und OCR installiert werden.
7. Auf der Konfigurationsseite `pdf_directory` zunächst auf `/share/mein-zuhause-pdf` belassen.
8. App starten; unter **Protokoll** eventuelle Fehlermeldungen prüfen.
9. Über **Weboberfläche öffnen** oder `http://HOME-ASSISTANT-IP:8099` starten.
10. Beim ersten Aufruf einen Administrator mit mindestens zwölfstelligem Passwort anlegen. Anschließend in **Verwaltung** weitere Familienmitglieder anlegen.

Hinweis: Die App verwendet absichtlich **kein Ingress**, damit sie auch direkt über den Browser am PC oder Smartphone erreichbar ist. Der Zugriff auf Port 8099 muss im Heimnetz möglich sein. Im VPN muss die Heimnetz-IP erreichbar sein. Keine Router-Portfreigabe für 8099 anlegen!

## 4. FRITZ!NAS für PDF-Dateien einbinden

1. An der FRITZ!Box ein USB-Speichermedium oder anderes unterstütztes NAS-Medium bereitstellen.
2. FRITZ!NAS/Heimnetzfreigabe (SMB) aktivieren und einen separaten FRITZ!Box-Benutzer mit nur den benötigten Berechtigungen einrichten.
3. In Home Assistant **Einstellungen → System → Speicher → Netzwerkspeicher hinzufügen** öffnen (Bezeichnungen können je nach Version abweichen).
4. Name z. B. `hausarchiv`, Verwendung **Share/Freigabe**, Protokoll **Samba/Windows (CIFS)**, Server `fritz.box` oder die IP der FRITZ!Box, Freigabename und Benutzer gemäß FRITZ!Box-Konfiguration.
5. Nach erfolgreicher Einbindung prüfen, ob das Verzeichnis unter `/share/hausarchiv` verfügbar ist. Der konkrete Pfad hängt von der Home-Assistant-Netzwerkspeicher-Einbindung ab.
6. In der App-Konfiguration `pdf_directory: /share/hausarchiv/MeinZuhause` setzen und App neu starten.
7. Testnotiz speichern. Prüfen, ob eine PDF-Datei in `MeinZuhause/<Kategorie>/` auf dem NAS erscheint.

WICHTIG: Nicht blind den Beispielpfad übernehmen. Bei einigen HA-Versionen und Freigabetypen wird ein Netzwerkspeicher nicht im App-Container unter dem angenommenen Pfad sichtbar. In diesem Fall zunächst `/share/mein-zuhause-pdf` verwenden und die PDFs über eine separate HA-Synchronisierung aufs NAS übertragen oder die App-Mount-Konfiguration anpassen. Die App meldet einen Exportfehler nur im Protokoll; sie zeigt derzeit keinen Exportstatus in der UI.

## 5. Bedienung

- Über **+ Neuer Eintrag** eine Notiz anlegen, Kategorie auswählen und Text formatieren.
- **Speichern** erzeugt bzw. überschreibt die zugehörige A4-PDF-Datei.
- Anschließend Dateien hochladen: JPG, PNG, WebP, PDF; max. 20 MB je Datei.
- Bei Upload wird deutsch/englische OCR ausgeführt. Das Suchfeld berücksichtigt OCR-Texte.
- Bei Bildern lässt sich die Breite in mm für die PDF-Ausgabe festlegen.
- Archivierte oder in den Papierkorb verschobene Einträge werden aus dem PDF-Zielordner entfernt; sie bleiben in der Datenbank bis zur endgültigen Löschung.
- Benutzer sehen in dieser Version **alle** Einträge gemeinsam. Es gibt keine privaten Einträge oder rollenbasierte Dokumentfreigabe.

## 6. Sicherung und Wiederherstellung

Die Datenbank und Anhänge liegen im persistenten App-Konfigurationsverzeichnis (`/config` im Container). Zusätzlich werden PDFs im konfigurierten Zielordner gespeichert. **PDFs sind kein vollständiges Backup.** Vor Updates Home-Assistant-Backup mit App-Daten erstellen und die PDFs separat sichern. Wiederherstellung zunächst in einer Testumgebung prüfen. Eine automatisierte externe Backup-Routine ist noch nicht enthalten.

## 7. Fehlersuche

- App nicht sichtbar: Repository-URL und Dateistruktur prüfen; Store neu laden.
- Build schlägt fehl: App-Protokoll und verfügbaren SSD-Speicher prüfen; ggf. Basisimage/Paketnamen an aktuelle HA-Version anpassen.
- Weboberfläche nicht erreichbar: App läuft? Port 8099 korrekt? IP/Firewall/VPN?
- OCR findet nichts: Fotoqualität, Spracheinstellung und App-Protokoll prüfen. Gescannte PDFs werden auf die ersten 10 Seiten begrenzt.
- Keine PDFs auf NAS: Exportpfad, Freigaberechte, Mount und App-Protokoll prüfen.
- Bei Fehlermeldungen aus dem Log keine Passwörter oder privaten Dokumente veröffentlichen.

## 8. Sicherheit und Einschränkungen

- Nur vertrauenswürdige Familienmitglieder zulassen; alle Benutzer können alle Einträge bearbeiten und löschen.
- Zugriff nur im LAN oder über VPN. HTTP innerhalb eines fremden/unvertrauenswürdigen Netzes ist nicht ausreichend.
- Session-Cookie mit HttpOnly/SameSite; Passwort-Hash PBKDF2; einfache Origin-Prüfung.
- **Noch keine** umfassende Penetrationsprüfung, CSRF-Token, Login-Ratenbegrenzung, MFA, Audit-Log, Verschlüsselung ruhender Daten, PDF-Job-Warteschlange, vollständige HTML-Formatübernahme, Revision-Wiederherstellungsoberfläche oder vollständige Dokumenten-OCR.
- Nicht als alleinige Ablage kritischer Versicherungs-, Ausweis- oder Zugangsdaten verwenden, bevor Backup und Sicherheitskonzept geprüft sind.
