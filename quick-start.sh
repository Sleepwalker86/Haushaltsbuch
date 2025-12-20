#!/bin/bash
# Quick-Start Script für Finanzapp mit Docker Hub Image
# Lädt die benötigten Docker Compose Dateien von GitHub herunter

set -e

echo "🚀 Finanzapp Quick-Start"
echo ""

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ist nicht installiert!"
    echo "   Bitte installieren Sie Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Prüfe ob Docker Compose verfügbar ist
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose ist nicht installiert!"
    echo "   Bitte installieren Sie Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Frage nach Datenbank-Typ
echo "Welche Datenbank möchten Sie verwenden?"
echo "1) Interne Datenbank (MySQL im Container)"
echo "2) Externe Datenbank"
read -p "Auswahl [1]: " DB_CHOICE
DB_CHOICE=${DB_CHOICE:-1}

# Dateien herunterladen
echo ""
echo "📥 Lade Docker Compose Dateien von GitHub..."

if [ "$DB_CHOICE" = "1" ]; then
    curl -s -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.yml
    COMPOSE_FILE="docker-compose.yml"
    echo "✅ docker-compose.yml heruntergeladen"
else
    curl -s -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/docker-compose.external-db.yml
    COMPOSE_FILE="docker-compose.external-db.yml"
    echo "✅ docker-compose.external-db.yml heruntergeladen"
fi

# .env.example herunterladen
if [ ! -f .env.example ]; then
    curl -s -O https://raw.githubusercontent.com/Sleepwalker86/Haushaltsbuch/main/.env.example
    echo "✅ .env.example heruntergeladen"
fi

# .env erstellen falls nicht vorhanden
if [ ! -f .env ]; then
    echo ""
    echo "📝 Erstelle .env Datei..."
    cp .env.example .env
    echo "✅ .env Datei erstellt"
    echo ""
    echo "⚠️  WICHTIG: Bitte bearbeiten Sie die .env Datei und passen Sie die Werte an!"
    echo "   nano .env"
    echo ""
    read -p "Drücken Sie Enter, wenn Sie die .env Datei bearbeitet haben..."
fi

# Docker Compose Datei anpassen (Image von Docker Hub verwenden)
echo ""
echo "🔧 Passe Docker Compose Datei an..."

# Frage nach Docker Hub Username
read -p "Docker Hub Username [sleepwalker86] (oder Enter für lokalen Build): " DOCKER_USERNAME
DOCKER_USERNAME=${DOCKER_USERNAME:-sleepwalker86}

if [ -n "$DOCKER_USERNAME" ] && [ "$DOCKER_USERNAME" != "" ]; then
    # Ersetze build durch image
    if [ "$DB_CHOICE" = "1" ]; then
        sed -i.bak 's|build:|# build:|g; s|context: .|# context: .|g; s|dockerfile: Dockerfile|# dockerfile: Dockerfile|g' docker-compose.yml
        sed -i.bak "/# dockerfile: Dockerfile/a\\
    image: ${DOCKER_USERNAME}/finanzapp:latest" docker-compose.yml
        rm docker-compose.yml.bak
        echo "✅ docker-compose.yml angepasst (verwendet Docker Hub Image)"
    else
        sed -i.bak 's|build:|# build:|g; s|context: .|# context: .|g; s|dockerfile: Dockerfile|# dockerfile: Dockerfile|g' docker-compose.external-db.yml
        sed -i.bak "/# dockerfile: Dockerfile/a\\
    image: ${DOCKER_USERNAME}/finanzapp:latest" docker-compose.external-db.yml
        rm docker-compose.external-db.yml.bak
        echo "✅ docker-compose.external-db.yml angepasst (verwendet Docker Hub Image)"
    fi
else
    echo "ℹ️  Verwende lokalen Build (Dockerfile wird benötigt)"
fi

# Container starten
echo ""
echo "🚀 Starte Container..."
if [ "$DB_CHOICE" = "1" ]; then
    docker compose up -d
else
    docker compose -f docker-compose.external-db.yml up -d
fi

echo ""
echo "✅ Container gestartet!"
echo ""
echo "📊 Logs anzeigen:"
if [ "$DB_CHOICE" = "1" ]; then
    echo "   docker compose logs -f app"
else
    echo "   docker compose -f docker-compose.external-db.yml logs -f app"
fi
echo ""
echo "🌐 Anwendung öffnen: http://localhost:5001"
echo ""
