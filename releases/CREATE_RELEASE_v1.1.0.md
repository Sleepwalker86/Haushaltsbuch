# Anleitung: Git Release v1.1.0 und Docker Image erstellen

## Schritt 1: Version prüfen

Die Version wurde bereits in `utils/version.py` auf `v1.1.0` aktualisiert.

## Schritt 2: Release-Notizen prüfen

Die Release-Notizen wurden erstellt:
- `releases/v1.1.0.md` - Vollständige Release Notes für GitHub
- `releases/v1.1.0-dockerhub.md` - Kurze Version für Docker Hub

Bitte prüfen und ggf. anpassen:
- Veröffentlichungsdatum aktualisieren
- Git Commit-Hash aktualisieren (wird automatisch beim Tag erstellt)
- GitHub-Username/Repository anpassen

## Schritt 3: Änderungen committen

```bash
# Status prüfen
git status

# Änderungen hinzufügen
git add utils/version.py releases/

# Commit erstellen
git commit -m "Release v1.1.0: Datenstruktur-Umstellung, Logging-System und Verbesserungen"
```

## Schritt 4: Git Tag erstellen

```bash
# Annotated Tag erstellen (empfohlen)
git tag -a v1.1.0 -m "Release v1.1.0

Hauptänderungen:
- Umstrukturierung: image/ → data/ (invoices, paperless, log)
- Umfassendes Logging-System mit Rotation
- Verbesserte Import-Statistiken
- Optimierte Docker Volumes
- Verbesserte Fehlerbehandlung

Siehe releases/v1.1.0.md für Details."

# Tag prüfen
git tag -l
git show v1.1.0
```

## Schritt 5: Tag und Commits pushen

```bash
# Commits pushen
git push origin main

# Tag pushen
git push origin v1.1.0
```

## Schritt 6: GitHub Release erstellen

1. Gehe zu: https://github.com/Sleepwalker86/pdf_to_data/releases/new
2. Wähle Tag: `v1.1.0`
3. Titel: `Release v1.1.0`
4. Beschreibung: Kopiere den Inhalt aus `releases/v1.1.0.md`
5. Klicke auf "Publish release"

## Schritt 7: Docker Image bauen und pushen

```bash
# Docker Image bauen und taggen
./build-and-push.sh 1.1.0

# Oder manuell:
docker build -t sleepwalker86/finanzapp:1.1.0 .
docker build -t sleepwalker86/finanzapp:latest .
docker push sleepwalker86/finanzapp:1.1.0
docker push sleepwalker86/finanzapp:latest
```

## Schritt 8: Docker Hub Release Notes hinzufügen

1. Gehe zu: https://hub.docker.com/r/sleepwalker86/finanzapp
2. Klicke auf den Tag `1.1.0`
3. Klicke auf "Edit"
4. Kopiere den Inhalt aus `releases/v1.1.0-dockerhub.md` in die Beschreibung
5. Speichern

## Verifikation

```bash
# Prüfe, ob Tag erstellt wurde
git tag -l

# Prüfe, ob Tag auf Remote existiert
git ls-remote --tags origin

# Prüfe Docker Hub
# https://hub.docker.com/r/sleepwalker86/finanzapp/tags
```

## Zusammenfassung der Änderungen in v1.1.0

### Breaking Changes
- **Datenstruktur**: `image/` → `data/invoices/` und `data/paperless/`
- **Logs**: `logs/` → `data/log/`
- **Docker Volumes**: Separates `logs`-Volume entfernt

### Neue Features
- Umfassendes Logging-System
- Verbesserte Import-Statistiken
- Optimierte Datenstruktur

### Wichtig für Upgrades
- Daten müssen manuell migriert werden (siehe Release Notes)
- Docker Volumes müssen angepasst werden
