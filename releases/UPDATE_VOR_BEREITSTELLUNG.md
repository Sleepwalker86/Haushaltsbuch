# Wichtige Schritte VOR dem Release v1.1.0

## ⚠️ WICHTIG: Diese Schritte müssen VOR dem Release durchgeführt werden!

### 1. Code-Änderungen committen

```bash
# Status prüfen
git status

# Alle Änderungen hinzufügen
git add .

# Commit erstellen
git commit -m "Fix: Migration-Verifikation für Beispiel-Migrationen verbessert

- Beispiel-Migrationen (nur Kommentare) werden jetzt übersprungen
- Verifikation prüft nur auf tatsächlich ausgeführte Statements
- Behebt Fehler bei Migration 002 (example_add_column.sql)"

# Pushen
git push origin main
```

### 2. Docker Image lokal bauen und testen

```bash
# Image lokal bauen (ohne Push)
docker build -t sleepwalker86/finanzapp:1.1.0 .
docker build -t sleepwalker86/finanzapp:latest .

# Optional: Lokal testen
docker compose down
# In docker-compose.yml: image auf sleepwalker86/finanzapp:1.1.0 ändern (temporär)
docker compose up -d
# Prüfen ob Migration funktioniert
docker compose logs app
```

### 3. Docker Image hochladen

```bash
# Mit dem Build-Script
./build-and-push.sh 1.1.0

# Oder manuell:
docker push sleepwalker86/finanzapp:1.1.0
docker push sleepwalker86/finanzapp:latest
```

### 4. Git Tag erstellen

```bash
# Tag erstellen
git tag -a v1.1.0 -m "Release v1.1.0

Hauptänderungen:
- Umstrukturierung: image/ → data/ (invoices, paperless, log)
- Umfassendes Logging-System mit Rotation
- Verbesserte Import-Statistiken
- Optimierte Docker Volumes
- Verbesserte Fehlerbehandlung
- Fix: Migration-Verifikation für Beispiel-Migrationen

Siehe releases/v1.1.0.md für Details."

# Tag pushen
git push origin v1.1.0
```

### 5. GitHub Release erstellen

1. Gehe zu: https://github.com/Sleepwalker86/Haushaltsbuch/releases/new
2. Wähle Tag: `v1.1.0`
3. Titel: `Release v1.1.0`
4. Beschreibung: Kopiere den Inhalt aus `releases/v1.1.0.md`
5. Klicke auf "Publish release"

### 6. Docker Hub Release Notes hinzufügen

1. Gehe zu: https://hub.docker.com/r/sleepwalker86/finanzapp
2. Klicke auf den Tag `1.1.0`
3. Klicke auf "Edit"
4. Kopiere den Inhalt aus `releases/v1.1.0-dockerhub.md`
5. Speichern

### 7. Update auf laufenden Systemen

**Erst NACH dem Image-Upload:**

```bash
# Container stoppen
docker compose down

# Neues Image pullen
docker compose pull

# Container neu starten
docker compose up -d

# Logs prüfen
docker compose logs app
```

## Reihenfolge Zusammenfassung

1. ✅ Code committen und pushen
2. ✅ Docker Image bauen und hochladen
3. ✅ Git Tag erstellen und pushen
4. ✅ GitHub Release erstellen
5. ✅ Docker Hub Release Notes hinzufügen
6. ✅ Auf laufenden Systemen: `docker compose pull && docker compose up -d`
