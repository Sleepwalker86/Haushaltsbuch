# Haushaltsbuch – CSV zu Dashboard

## Übersicht

Dieses Projekt ist ein persönliches Haushaltsbuch, das Bankumsätze aus CSV-Dateien einliest, strukturiert in eine MySQL/MariaDB-Datenbank speichert und sie anschließend in einer responsiven Web-App visualisiert.

Die Weboberfläche (Flask + Bootstrap) bietet:

- Manuelles Erfassen von Buchungen (z. B. Barzahlungen)
- Automatisierten CSV-Import (z. B. aus Online-Banking-Exporten)
- Kategorisierung von Umsätzen (inkl. Unterkategorie)
- Dashboard mit Diagrammen (Kategorien, Ausgaben, Einzahlungen)
- Verwaltung von Konten (Name, IBAN, Beschreibung)
- Zeitgesteuerten Import über systemd-Timer auf dem Server
- Erweiterte Filterung (Jahr, Monat, Konto, Kategorie, Unterkategorie)
- CSV-Export der gefilterten Buchungen
- Paperless-Integration: Dokumente fotografieren und automatisch an Paperless senden
- Manuell bearbeitete Buchungen kennzeichnen (`manually_edit` Toggle)

---

## Funktionen im Detail

### Dashboard (`/dashboard`)

- **Filter**: Jahr, Monat, Konto (IBAN), Kategorie (Dropdown), Unterkategorie (Freitext).
- **Diagramme (Chart.js)**:
  - Kategorien (Einnahmen/Ausgaben) als gestapeltes Balkendiagramm inkl. Summen (gesamt Einnahmen/Ausgaben).
  - Ausgaben (Kategorien) als Tortendiagramm.
  - Einzahlungen nach IBAN als Balkendiagramm.
- **Buchungstabelle**:
  - Spalten: Datum, Art, Beschreibung, Soll, Haben, Kategorie, Unterkategorie.
  - Paginierung (30 Einträge pro Seite).
  - Bearbeiten-Button je Buchung → `/edit/<id>`.
  - **CSV-Export**: Button zum Herunterladen aller gefilterten Buchungen als CSV-Datei.

### Buchung erfassen (`/`)

- Felder:
  - Datum
  - Typ (Ausgaben / Einnahmen)
  - Konto (Dropdown aus `konten`-Tabelle, Pflichtfeld)
  - Kategorie (Dropdown aus `keyword_category`-Tabelle)
  - Unterkategorie (`kategorie2`, Freitext)
  - Betrag (Komma/Punkt als Dezimaltrenner)
  - Beschreibung
- Speicherung:
  - Tabelle `buchungen`
  - Ausgaben → `soll`, Einnahmen → `haben`
  - `manually_edit = 1` zur Kennzeichnung manueller Einträge.

### Buchung bearbeiten / löschen (`/edit/<id>`, `/delete/<id>`)

- Bearbeiten:
  - Alle Felder der Buchung änderbar.
  - **Manually_edit Toggle**: Switch zum Ein-/Ausschalten der `manually_edit`-Kennzeichnung.
    - Wenn aktiviert: Buchung wird als manuell bearbeitet markiert (neue Kategorien werden nicht automatisch gesetzt).
    - Standard: Beim Speichern wird `manually_edit = 1` gesetzt, kann aber deaktiviert werden.
- Löschen:
  - Separater Button mit Sicherheitsabfrage (`confirm`).
  - Löscht aus `buchungen` und leitet zurück ins Dashboard inkl. Filter.

### Einstellungen & Kontenverwaltung (`/settings`)

Zwei Tabs:

- **CSV Upload & Import**
  - CSV-Datei hochladen (`/upload_csv`): Datei wird in den Ordner `import/` gespeichert.
  - Buttons:
    - „Kategorien neu laden“ → ruft `reload_category.py` auf.
    - „CSV Daten einlesen“ → ruft `import_data.py` auf.

- **Konten & Einstellungen**
  - Konto anlegen/bearbeiten:
    - Name
    - Beschreibung
    - IBAN
  - Liste vorhandener Konten aus Tabelle `konten` mit Bearbeiten- und Löschen-Icon:
    - Klick lädt das Konto in das Formular zum Editieren (selber Tab).
    - Löschen mit Sicherheitsabfrage.

- **Kategorien & Schlüsselwörter**
  - **Kategorien-Stammdaten**: Kategorien aus der `category`-Tabelle anlegen und löschen.
  - **Schlüsselwort-Zuordnungen**: Zuordnungen zwischen Schlüsselwörtern und Kategorien in der `keyword_category`-Tabelle verwalten (anlegen, bearbeiten, löschen).

- **Paperless**
  - Paperless-API-Konfiguration:
    - Paperless-URL/IP-Adresse
    - API-Token
    - Dokumententyp-ID

---

## Technische Anforderungen

- **Betriebssystem**: Debian/Ubuntu mit systemd (getestet auf Debian 12)
- **Python**: 3.11
- **Datenbank**: MySQL oder MariaDB (z. B. MariaDB 10.x)
- **Pakete (in venv)**:
  - `flask`
  - `mysql-connector-python`
  - `pandas`
  - `python-dateutil`
  - `requests` (für Paperless-API)
- **Systempakete**:
  - `python3`, `python3-venv`, `python3-pip`
  - `mariadb-client`
  - `git`, `curl`, `ca-certificates`

---

## Installation mit Docker

Die einfachste Methode, die Anwendung zu installieren, ist die Verwendung von Docker und Docker Compose.

### Voraussetzungen

- Docker (Version 20.10 oder höher)
- Docker Compose (Version 1.29 oder höher)

### Option 1: Interne Datenbank (MySQL im Container)

1. **Docker Compose Dateien herunterladen:**
   ```bash
   curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.yml
   curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/.env.example
   ```

2. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Wichtige Einstellungen:
   - `MYSQL_ROOT_PASSWORD`: Root-Passwort für MySQL
   - `MYSQL_DATABASE`: Name der Datenbank (Standard: Haushaltsbuch)
   - `MYSQL_USER`: Datenbankbenutzer
   - `MYSQL_PASSWORD`: Passwort für den Datenbankbenutzer
   - `SECRET_KEY`: Sicherer Secret Key für Flask (wichtig!)

3. **Docker Compose Datei anpassen (falls Docker Hub Image verwendet wird):**
   
   Öffnen Sie `docker-compose.yml` und ändern Sie:
   ```yaml
   # Statt:
   build:
     context: .
     dockerfile: Dockerfile
   
   # Verwenden Sie (mit Ihrem Docker Hub Username):
   image: dein-username/finanzapp:latest
   ```

4. **Container starten:**
   ```bash
   docker compose up -d
   ```

5. **Logs prüfen:**
   ```bash
   docker compose logs -f app
   ```

6. **Anwendung aufrufen:**
   Öffnen Sie im Browser: `http://localhost:5001` oder `http://host-ip:5001`

### Option 2: Externe Datenbank

1. **Docker Compose Dateien herunterladen:**
   ```bash
   curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.external-db.yml
   curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/.env.example
   ```

2. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Wichtige Einstellungen:
   - `DB_HOST`: IP-Adresse oder Hostname der externen Datenbank
   - `DB_USER`: Datenbankbenutzer
   - `DB_PASSWORD`: Passwort für den Datenbankbenutzer
   - `DB_NAME`: Name der Datenbank
   - `SECRET_KEY`: Sicherer Secret Key für Flask (wichtig!)

3. **Docker Compose Datei anpassen (falls Docker Hub Image verwendet wird):**
   
   Öffnen Sie `docker-compose.external-db.yml` und ändern Sie:
   ```yaml
   # Statt:
   build:
     context: .
     dockerfile: Dockerfile
   
   # Verwenden Sie (mit Ihrem Docker Hub Username):
   image: dein-username/finanzapp:latest
   ```

4. **Container starten:**
   ```bash
   docker compose -f docker-compose.external-db.yml up -d
   ```

5. **Logs prüfen:**
   ```bash
   docker compose -f docker-compose.external-db.yml logs -f app
   ```

6. **Anwendung aufrufen:**
   Öffnen Sie im Browser: `http://localhost:5001` oder `http://host-ip:5001`

### Wichtige Hinweise

- **Externe Datenbank:** Stellen Sie sicher, dass die Datenbank Remote-Verbindungen erlaubt (MySQL `bind-address = 0.0.0.0`)
- **Firewall:** Port 3306 muss vom Container aus erreichbar sein
- **Benutzerrechte:** Der Datenbankbenutzer muss die entsprechenden Rechte haben (CREATE, INSERT, UPDATE, DELETE, SELECT)
- **Nach .env Änderungen:** Container neu starten mit `docker compose restart app`

### Weitere Informationen

Für detaillierte Docker-Dokumentation siehe `DOCKER.md` im Repository.

---

## Installation (Server)

### 1. Repository nach `/opt` klonen

```bash
sudo git clone https://github.com/Sleepwalker86/Haushaltsbuch.git /opt/finanzapp
cd /opt/finanzapp
```

### 2. Installationsscript ausführen

```bash
sudo chmod +x install.sh
sudo ./install.sh
```

Das Script erledigt:

1. `apt update` und Installation der Systempakete.
2. Anlage des Users `finanzapp` (falls nicht vorhanden).
3. Klonen/Update des Repos unter `/opt/finanzapp` (als User `finanzapp`).
4. Anlage des Ordners `import/`.
5. Erzeugung einer Python-virtualenv unter `/opt/finanzapp/venv`.
6. Installation der Python-Abhängigkeiten in der venv.
7. Anlegen von `config.json` (falls nicht vorhanden) mit interaktiver Abfrage von:
   - DB-Host
   - DB-User
   - DB-Passwort
   - DB-Name
8. Anlegen und Aktivieren der systemd-Units:
   - `finanzapp.service` – startet die Flask-App (Produktionsmodus, kein Debug).
   - `finanzapp-import.service` – einmaliger CSV-Import via `import_data.py`.
   - `finanzapp-import.timer` – ruft den Import-Service alle 10 Minuten auf.

### 3. Services prüfen

```bash
systemctl status finanzapp.service
systemctl status finanzapp-import.timer
```

Die App ist i. d. R. unter `http://SERVER-IP:5001` erreichbar.

---

## Deinstallation (Server)

Um die Anwendung inklusive systemd-Services sauber zu entfernen, gibt es ein eigenes Script `uninstall.sh`.

```bash
cd /opt/finanzapp
sudo chmod +x uninstall.sh
sudo ./uninstall.sh
```

Das Script erledigt:

1. Stoppen und Deaktivieren von:
   - `finanzapp.service`
   - `finanzapp-import.service`
   - `finanzapp-import.timer`
2. Entfernen der systemd-Unit-Dateien unter `/etc/systemd/system/`.
3. `systemctl daemon-reload` und `systemctl reset-failed`.
4. Löschen des App-Verzeichnisses `/opt/finanzapp`.
5. Optionales Löschen des Benutzers `finanzapp` (nach Rückfrage).

Die MySQL-Datenbank und ihre Inhalte werden **nicht** gelöscht, damit deine Buchungsdaten erhalten bleiben.

---

## Lokale Entwicklung

### 1. Klonen & venv

```bash
git clone https://github.com/Sleepwalker86/Haushaltsbuch.git
cd Haushaltsbuch

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. `config.json` anlegen (lokal)

```json
{
  "DB_CONFIG": {
    "host": "127.0.0.1",
    "user": "dein_user",
    "password": "dein_passwort",
    "database": "Haushaltsbuch"
  }
}
```

### 3. App lokal starten

```bash
export FLASK_DEBUG=1
python app.py
```

Dann ist die App unter `http://127.0.0.1:5001` erreichbar.

---

## Paperless-Integration

### Funktionen

1. **Dokumente fotografieren** (`/paperless`):
   - Direkter Zugriff auf die iPhone/iPad-Kamera über die Web-Oberfläche.
   - Unterstützte Formate: JPG, PNG, HEIC, HEIF, PDF.
   - Bilder werden im Ordner `image/` gespeichert.

2. **Automatischer Upload**:
   - Das Skript `import_data.py` prüft bei jedem Lauf (alle 10 Minuten via Timer) den `image/`-Ordner.
   - Neue Bilder werden automatisch an die konfigurierte Paperless-Instanz gesendet.
   - Bei erfolgreichem Upload werden die Bilder gelöscht.
   - Bei Fehlern bleiben die Bilder erhalten für manuelle Nachbearbeitung.

3. **Konfiguration**:
   - In den Einstellungen (Tab "Paperless") können konfiguriert werden:
     - Paperless-URL/IP-Adresse (z. B. `http://192.168.1.100:8000`)
     - API-Token (aus den Paperless-Einstellungen)
     - Dokumententyp-ID (optional, für automatische Kategorisierung)

### Voraussetzungen

- Paperless-ngx oder Paperless-ng Instanz muss erreichbar sein.
- API-Token muss in Paperless generiert werden (Einstellungen → API-Token).
- Die Konfiguration wird in `config.json` unter `PAPERLESS` gespeichert.

---

## Nutzung

1. **Einstellungen → Konten**: Konten anlegen (Name, IBAN, Beschreibung).
2. **CSV Upload**:
   - Im Tab „Upload“ CSV hochladen (landet im `import/`-Ordner).
   - „CSV Daten einlesen“ ausführen oder Timer abwarten.
3. **Dashboard** ansehen und filtern:
   - Jahr, Monat, Konto, Kategorie, Unterkategorie.
   - Gefilterte Buchungen als CSV exportieren.
4. **Buchungen manuell erfassen** unter `/`.
5. **Buchungen bearbeiten oder löschen** über die Tabelle im Dashboard.
   - `manually_edit`-Status per Toggle ein-/ausschalten.
6. **Paperless-Integration**:
   - Dokumente fotografieren unter `/paperless`.
   - Automatischer Upload erfolgt beim nächsten CSV-Import (alle 10 Minuten).

---

## Lizenz / Nutzung

© 2025 Sascha Moritz

Der Quellcode darf für den **eigenen Gebrauch** angepasst und erweitert werden.

Eine **Weitergabe, Veröffentlichung oder kommerzielle Nutzung veränderter Versionen ist nicht gestattet**.

Wenn du den Code in einem anderen Kontext einsetzen willst (z. B. in einem Unternehmen oder als Open‑Source‑Projekt), kläre dies bitte vorher mit dem Autor.

---

## Haftungsausschluss

Dieses Projekt wird ohne Garantie bereitgestellt. Es gibt keine Gewähr für Richtigkeit, Vollständigkeit oder Eignung für einen bestimmten Zweck. Die Nutzung erfolgt auf eigene Verantwortung – insbesondere im Hinblick auf den Umgang mit sensiblen Finanzdaten.
