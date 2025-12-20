# Docker Hub Veröffentlichung

## Image auf Docker Hub hochladen

### 1. Docker Hub Account erstellen
- Registrieren Sie sich auf https://hub.docker.com
- Erstellen Sie ein Repository (z.B. `finanzapp`)

### 2. Image bauen und taggen

**WICHTIG für Multi-Architecture Support (ARM64, AMD64):**

```bash
# Docker Buildx aktivieren (für Multi-Architecture Builds)
docker buildx create --use --name multiarch-builder
docker buildx inspect --bootstrap

# Multi-Architecture Build (für mehrere Plattformen)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag sleepwalker86/finanzapp:latest \
  --push \
  .

# Optional: Version taggen
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag sleepwalker86/finanzapp:v1.0.0 \
  --push \
  .
```

**Alternative: Nur für eine Architektur (schneller, aber nur für diese Architektur):**

```bash
# Nur für AMD64 (Standard x86_64)
docker build -t sleepwalker86/finanzapp:latest .

# Nur für ARM64 (z.B. Apple Silicon, Raspberry Pi)
docker build --platform linux/arm64 -t sleepwalker86/finanzapp:latest .
```

### 3. Bei Docker Hub anmelden

```bash
docker login
```

### 4. Image hochladen

**Wenn Sie Multi-Architecture Build verwendet haben:**
- Das Image wurde bereits mit `--push` hochgeladen, kein separater Push nötig!

**Wenn Sie nur für eine Architektur gebaut haben:**

```bash
# Bei Docker Hub anmelden (falls noch nicht geschehen)
docker login

# Latest Version hochladen
docker push sleepwalker86/finanzapp:latest

# Versionierte Tags hochladen
docker push sleepwalker86/finanzapp:v1.0.0
```

## Docker Hub Repository Beschreibung

Fügen Sie folgende Informationen in die Docker Hub Repository Beschreibung ein:

```markdown
# Finanzapp - Haushaltsbuch

Eine Flask-basierte Web-Anwendung zur Verwaltung von Haushaltsbuchungen.

## Quick Start

```bash
# Repository klonen (für docker-compose Dateien)
git clone https://github.com/Sleepwalker86/Haushaltsbuch.git
cd Haushaltsbuch

# Mit interner Datenbank starten
docker compose up -d

# Mit externer Datenbank starten
docker compose -f docker-compose.external-db.yml up -d
```

## Dokumentation

- **Vollständige Docker-Dokumentation**: Siehe `DOCKER.md` im Repository
- **GitHub Repository**: https://github.com/Sleepwalker86/Haushaltsbuch
- **README**: Siehe `README.md` im Repository

## Wichtig

Die `docker-compose.yml` Dateien sind **nicht** im Docker-Image enthalten.
Bitte klonen Sie das GitHub-Repository, um die Compose-Dateien zu erhalten.

## Verwendung

```bash
# Image direkt verwenden
docker run -d \
  -p 5001:5001 \
  -e DB_HOST=192.168.10.99 \
  -e DB_USER=username \
  -e DB_PASSWORD=password \
  -e DB_NAME=Haushaltsbuch \
  -e SECRET_KEY=your-secret-key \
  sleepwalker86/finanzapp:latest
```

## Tags

- `latest` - Neueste Version
- `v1.0.0` - Versionierte Releases
```

## Automatisches Build Setup (Optional)

### GitHub Actions für automatische Builds

Erstellen Sie `.github/workflows/docker-publish.yml`:

```yaml
name: Docker Build and Push

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: sleepwalker86/finanzapp
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

## GitHub Secrets konfigurieren

1. Gehen Sie zu: Repository → Settings → Secrets → Actions
2. Fügen Sie hinzu:
   - `DOCKER_USERNAME`: Ihr Docker Hub Benutzername
   - `DOCKER_PASSWORD`: Ihr Docker Hub Token (nicht Passwort!)

## Verwendung durch Endbenutzer

### Option 1: GitHub Repository klonen (Empfohlen)

```bash
git clone https://github.com/Sleepwalker86/Haushaltsbuch.git
cd Haushaltsbuch
docker compose up -d
```

### Option 2: Nur YAML-Dateien herunterladen

```bash
# docker-compose.yml
curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.yml

# docker-compose.external-db.yml
curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.external-db.yml

# .env.example
curl -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/.env.example
```

### Option 3: Image direkt verwenden (ohne Compose)

```bash
docker run -d \
  --name finanzapp \
  -p 5001:5001 \
  -v $(pwd)/import:/app/import \
  -v $(pwd)/image:/app/image \
  -e DB_HOST=192.168.10.99 \
  -e DB_USER=username \
  -e DB_PASSWORD=password \
  -e DB_NAME=Haushaltsbuch \
  -e SECRET_KEY=your-secret-key \
  sleepwalker86/finanzapp:latest
```
