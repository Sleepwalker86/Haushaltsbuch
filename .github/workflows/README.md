# GitHub Actions Workflows

Dieses Verzeichnis enthält die CI/CD-Pipeline für die Finanzapp.

## Workflows

### 1. `ci.yml` - Haupt-CI-Pipeline
Wird bei jedem Push und Pull Request ausgeführt:
- **Code Quality**: Linting mit flake8, pylint
- **Docker Build**: Testet ob Docker Image erfolgreich gebaut werden kann
- **Migrations**: Testet Datenbank-Migrationen mit MySQL
- **Imports**: Prüft ob alle Python-Imports funktionieren
- **Security**: Sicherheitsprüfungen mit Bandit
- **Documentation**: Prüft README und Dokumentation

### 2. `docker-build.yml` - Docker Build & Push
Wird ausgeführt bei:
- Push zu `main` Branch
- Erstellung eines Version-Tags (z.B. `v1.0.3`)
- Manueller Auslösung via `workflow_dispatch`

Baut und pusht das Docker Image zu Docker Hub:
- Multi-Architecture (AMD64 + ARM64)
- Taggt mit Versionsnummer und `latest`

**Benötigte Secrets:**
- `DOCKER_USERNAME`: Docker Hub Benutzername
- `DOCKER_PASSWORD`: Docker Hub Token/Passwort

### 3. `code-quality.yml` - Erweiterte Code-Qualität
Fokus auf Code-Qualität:
- Black Code-Formatierung
- isort Import-Sortierung
- flake8 Linting
- mypy Type-Checking

### 4. `release.yml` - GitHub Release erstellen
Wird bei Erstellung eines Version-Tags ausgeführt:
- Erstellt automatisch ein GitHub Release
- Verwendet `RELEASE_NOTES_X.X.X.md` als Release-Notizen
- Verlinkt zum Docker Image auf Docker Hub

## Secrets einrichten

In GitHub Repository Settings → Secrets and variables → Actions:

1. **DOCKER_USERNAME**: Dein Docker Hub Benutzername
2. **DOCKER_PASSWORD**: Docker Hub Access Token (nicht Passwort!)

Docker Hub Token erstellen:
1. Docker Hub → Account Settings → Security
2. "New Access Token" erstellen
3. Token kopieren und als Secret speichern

## Workflow manuell auslösen

```bash
# Via GitHub Web-Interface:
# Actions → Workflow auswählen → "Run workflow"

# Via GitHub CLI:
gh workflow run docker-build.yml -f version=1.0.3
```

## Lokale Tests

Vor dem Commit kannst du einige Checks lokal ausführen:

```bash
# Code-Formatierung prüfen
black --check .

# Code formatieren
black .

# Linting
flake8 .

# Syntax prüfen
python -m py_compile app.py
find . -name "*.py" -exec python -m py_compile {} \;
```

## Workflow-Status

Die Workflows zeigen ihren Status direkt im GitHub Repository:
- ✅ Grün: Alle Checks erfolgreich
- ❌ Rot: Mindestens ein Check fehlgeschlagen
- 🟡 Gelb: Workflow läuft noch

Bei fehlgeschlagenen Checks:
1. Klicke auf den fehlgeschlagenen Check
2. Prüfe die Logs
3. Behebe die Fehler
4. Committe und pushe erneut
