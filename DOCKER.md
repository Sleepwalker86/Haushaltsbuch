# Docker Setup für Finanzapp

Dieses Projekt kann mit Docker und Docker Compose ausgeführt werden.

## Voraussetzungen

- Docker (Version 20.10 oder höher)
- Docker Compose (Version 1.29 oder höher)

## Docker Hub Image

Das fertige Docker-Image ist auf Docker Hub verfügbar:

```bash
docker pull sleepwalker86/finanzapp:latest
```

**Wichtig:** Die `docker-compose.yml` Dateien sind **nicht** im Docker-Image enthalten. 
Sie können die YAML-Dateien direkt von GitHub herunterladen:

```bash
# docker-compose.yml (für interne Datenbank)
curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.yml

# docker-compose.external-db.yml (für externe Datenbank)
curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.external-db.yml

# .env.example (Vorlage für Umgebungsvariablen)
curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/.env.example
```

**Alternative:** Das komplette Repository klonen:

```bash
git clone https://github.com/Sleepwalker86/Haushaltsbuch.git
cd Haushaltsbuch
```

## Schnellstart

### Option A: Mit Docker Hub Image (Empfohlen)

1. **Docker Compose Dateien herunterladen:**
   ```bash
   # Für interne Datenbank
   curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.yml
   
   # Für externe Datenbank
   curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.external-db.yml
   
   # .env Vorlage
   curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/.env.example
   ```

2. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   ```
   
   Bearbeiten Sie die `.env` Datei und passen Sie die Werte an:
   - `MYSQL_ROOT_PASSWORD`: Root-Passwort für MySQL (nur interne DB)
   - `MYSQL_PASSWORD`: Passwort für den Datenbankbenutzer (nur interne DB)
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Für externe DB
   - `SECRET_KEY`: Sicherer Secret Key für Flask (wichtig für Produktion!)
   - Weitere Konfigurationen nach Bedarf

3. **Docker Compose Datei anpassen (Image von Docker Hub verwenden):**
   
   Öffnen Sie `docker-compose.yml` oder `docker-compose.external-db.yml` und ändern Sie:
   ```yaml
   # Statt:
   build:
     context: .
     dockerfile: Dockerfile
   
   # Verwenden Sie:
   image: sleepwalker86/finanzapp:latest
   ```

4. **Container starten:**
   ```bash
   # Für interne Datenbank
   docker compose up -d
   
   # Für externe Datenbank
   docker compose -f docker-compose.external-db.yml up -d
   ```

5. **Anwendung aufrufen:**
   Öffnen Sie im Browser: `http://localhost:5001` oder `http://host-ip:5001`

### Option B: Repository klonen (für Entwicklung)

1. **Repository klonen:**
   ```bash
   git clone https://github.com/Sleepwalker86/Haushaltsbuch.git
   cd Haushaltsbuch
   ```

2. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   ```
   
   Bearbeiten Sie die `.env` Datei und passen Sie die Werte an.

3. **Container starten:**
   ```bash
   docker compose up -d
   ```

4. **Anwendung aufrufen:**
   Öffnen Sie im Browser: `http://localhost:5001` oder `http://host-ip:5001`

## Befehle

### Container starten
```bash
# Für interne Datenbank
docker compose up -d

# Für externe Datenbank
docker compose -f docker-compose.external-db.yml up -d
```

### Container stoppen
```bash
# Für interne Datenbank
docker compose down

# Für externe Datenbank
docker compose -f docker-compose.external-db.yml down
```

### Container stoppen und Volumes löschen
```bash
# Für interne Datenbank
docker compose down -v

# Für externe Datenbank
docker compose -f docker-compose.external-db.yml down
```

### Logs anzeigen
```bash
# Für interne Datenbank
docker compose logs -f app

# Für externe Datenbank
docker compose -f docker-compose.external-db.yml logs -f app
```

### Datenbank-Logs anzeigen
```bash
# Nur für interne Datenbank verfügbar
docker compose logs -f db
```

### In Container einsteigen
```bash
# Für interne Datenbank
docker compose exec app bash

# Für externe Datenbank
docker compose -f docker-compose.external-db.yml exec app bash
```

### Datenbank-Container (nur interne DB)
```bash
docker compose exec db mysql -u root -p
```

### Container neu bauen
```bash
# Für interne Datenbank
docker compose build --no-cache
docker compose up -d

# Für externe Datenbank
docker compose -f docker-compose.external-db.yml build --no-cache
docker compose -f docker-compose.external-db.yml up -d
```

### Container neu starten (nach .env Änderungen)
```bash
# Für interne Datenbank
docker compose restart app

# Für externe Datenbank
docker compose -f docker-compose.external-db.yml restart app
```

## Verzeichnisse

Die folgenden Verzeichnisse werden als Volumes gemountet:
- `./import` - CSV-Dateien zum Importieren
- `./image` - Bilder für Paperless

**Hinweis:** Die `config.json` wird automatisch im Container erstellt und bei jedem Start aus den Umgebungsvariablen aktualisiert. Sie wird nicht als Volume gemountet.

## Datenbank

### Interne Datenbank (Standard)

Die MySQL-Datenbank wird automatisch initialisiert beim ersten Start. Die Daten werden in einem Docker Volume (`mysql_data`) gespeichert und bleiben auch nach dem Stoppen der Container erhalten.

### Externe Datenbank verwenden

Wenn Sie eine externe MySQL/MariaDB-Datenbank verwenden möchten:

1. **Erstellen Sie eine `.env` Datei** (falls noch nicht vorhanden):
   ```bash
   cp .env.example .env
   ```

2. **Setzen Sie folgende Parameter in der `.env` Datei:**
   ```bash
   # Externe Datenbank (ERFORDERLICH)
   DB_HOST=192.168.10.xx          # IP-Adresse oder Hostname der externen DB
   DB_USER=db_username                     # Datenbankbenutzer
   DB_PASSWORD=password                # Passwort
   DB_NAME=Haushaltsbuch      # Datenbankname
   
   # Flask Konfiguration
   SECRET_KEY=ihr-geheimer-schlüssel-hier
   APP_PORT=5001
   FLASK_DEBUG=0
   
   # Paperless (optional)
   PAPERLESS_ENABLED=false
   ```

3. **Starten Sie nur den App-Container:**
   ```bash
   docker compose -f docker-compose.external-db.yml up -d
   ```

4. **Prüfen Sie die Logs:**
   ```bash
   docker compose -f docker-compose.external-db.yml logs -f app
   ```

**Wichtig:**
- Die externe Datenbank muss vom Docker-Container aus erreichbar sein
- Stellen Sie sicher, dass die externe Datenbank Remote-Verbindungen erlaubt
- Der Datenbankbenutzer muss die entsprechenden Rechte haben (CREATE, INSERT, UPDATE, DELETE, SELECT)

## Umgebungsvariablen

Alle wichtigen Konfigurationen werden über die `.env` Datei gesteuert:

### Für interne Datenbank (docker-compose.yml):
- **MYSQL_ROOT_PASSWORD**: Root-Passwort für MySQL
- **MYSQL_DATABASE**: Name der Datenbank
- **MYSQL_USER**: Datenbankbenutzer
- **MYSQL_PASSWORD**: Passwort für den Datenbankbenutzer
- **MYSQL_PORT**: Port für MySQL (Standard: 3306)
- **APP_PORT**: Port für die Flask-Anwendung (Standard: 5001)
- **FLASK_DEBUG**: Debug-Modus (0 oder 1)
- **SECRET_KEY**: Secret Key für Flask (wichtig!)
- **PAPERLESS_***: Paperless-Konfiguration (optional)

### Für externe Datenbank (docker-compose.external-db.yml):
- **DB_HOST**: IP-Adresse oder Hostname der externen Datenbank (ERFORDERLICH)
- **DB_USER**: Datenbankbenutzer (ERFORDERLICH)
- **DB_PASSWORD**: Passwort für den Datenbankbenutzer (ERFORDERLICH)
- **DB_NAME**: Name der Datenbank (ERFORDERLICH)
- **APP_PORT**: Port für die Flask-Anwendung (Standard: 5001)
- **FLASK_DEBUG**: Debug-Modus (0 oder 1)
- **SECRET_KEY**: Secret Key für Flask (wichtig!)
- **PAPERLESS_***: Paperless-Konfiguration (optional)

## Troubleshooting

### Container startet nicht
- Prüfen Sie die Logs: 
  - Interne DB: `docker compose logs app`
  - Externe DB: `docker compose -f docker-compose.external-db.yml logs app`
- Prüfen Sie, ob die `.env` Datei existiert und korrekt konfiguriert ist
- Prüfen Sie, ob Port 5001 bereits belegt ist
- Nach Änderungen in der `.env` Datei Container neu starten (siehe "Container neu starten")

### Datenbank-Verbindungsfehler
- **Interne Datenbank:**
  - Warten Sie, bis die Datenbank vollständig gestartet ist (Healthcheck)
  - Prüfen Sie die Datenbank-Logs: `docker compose logs db`
- **Externe Datenbank:**
  - Prüfen Sie, ob die Datenbank erreichbar ist (Netzwerk/Firewall)
  - Prüfen Sie MySQL bind-address (muss `0.0.0.0` sein, nicht `127.0.0.1`)
  - Prüfen Sie Benutzerrechte für Remote-Verbindungen
- Prüfen Sie die Umgebungsvariablen in der `.env` Datei
- Prüfen Sie die `config.json` im Container: `docker compose exec app cat /app/config.json`

### Daten gehen verloren
- **Interne Datenbank:**
  - Die Datenbank-Daten werden im Volume `mysql_data` gespeichert
  - Bei `docker compose down -v` werden die Volumes gelöscht!
  - Für Backups: `docker compose exec db mysqldump -u root -p Haushaltsbuch > backup.sql`
- **Externe Datenbank:**
  - Daten werden auf dem externen MySQL-Server gespeichert
  - Backups müssen direkt auf dem DB-Server durchgeführt werden
