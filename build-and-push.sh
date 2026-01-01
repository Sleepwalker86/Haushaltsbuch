#!/bin/bash
# Script zum Bauen und Hochladen des Docker-Images auf Docker Hub
# Unterstützt Multi-Architecture Builds (AMD64 und ARM64)

set -e

DOCKER_USERNAME="sleepwalker86"
IMAGE_NAME="finanzapp"
VERSION="${1:-1.0.2}"

echo "🐳 Docker Image Build und Push Script"
echo "======================================"
echo ""
echo "📦 Version: ${VERSION}"
echo ""

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ist nicht installiert!"
    exit 1
fi

# Prüfe ob bei Docker Hub angemeldet
if ! docker info | grep -q "Username"; then
    echo "⚠️  Sie sind nicht bei Docker Hub angemeldet."
    echo "   Bitte führen Sie 'docker login' aus."
    read -p "Jetzt anmelden? (j/n) [j]: " LOGIN_NOW
    LOGIN_NOW=${LOGIN_NOW:-j}
    if [[ "$LOGIN_NOW" =~ ^[JjYy]$ ]]; then
        docker login
    else
        echo "❌ Abgebrochen. Bitte melden Sie sich zuerst an."
        exit 1
    fi
fi

# Frage nach Build-Typ
echo ""
echo "Welchen Build-Typ möchten Sie verwenden?"
echo "1) Multi-Architecture (AMD64 + ARM64) - Empfohlen für Docker Hub"
echo "2) Nur AMD64 (x86_64)"
echo "3) Nur ARM64 (Apple Silicon, Raspberry Pi)"
read -p "Auswahl [1]: " BUILD_TYPE
BUILD_TYPE=${BUILD_TYPE:-1}

# Docker Buildx für Multi-Architecture Setup
if [ "$BUILD_TYPE" = "1" ]; then
    echo ""
    echo "🔧 Richte Docker Buildx für Multi-Architecture ein..."
    
    # Prüfe ob Buildx verfügbar ist
    if ! docker buildx version &> /dev/null; then
        echo "❌ Docker Buildx ist nicht verfügbar!"
        echo "   Bitte installieren Sie Docker Buildx oder verwenden Sie Option 2 oder 3."
        exit 1
    fi
    
    # Erstelle Builder-Instanz falls nicht vorhanden
    if ! docker buildx ls | grep -q "multiarch-builder"; then
        echo "   Erstelle Multi-Architecture Builder..."
        docker buildx create --name multiarch-builder --use
        docker buildx inspect --bootstrap
    else
        echo "   Verwende vorhandenen Multi-Architecture Builder..."
        docker buildx use multiarch-builder
    fi
    
    echo ""
    echo "🏗️  Baue Image für mehrere Architekturen (AMD64 + ARM64)..."
    echo "   Image: ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}"
    echo "   Image: ${DOCKER_USERNAME}/${IMAGE_NAME}:latest"
    
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --tag ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION} \
        --tag ${DOCKER_USERNAME}/${IMAGE_NAME}:latest \
        --push \
        .
    
    echo ""
    echo "✅ Image erfolgreich gebaut und hochgeladen!"
    echo "   Verfügbar für: AMD64 (x86_64) und ARM64"
    echo "   Tags: ${VERSION} und latest"
    
elif [ "$BUILD_TYPE" = "2" ]; then
    echo ""
    echo "🏗️  Baue Image für AMD64 (x86_64)..."
    docker build --platform linux/amd64 \
        -t ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION} \
        -t ${DOCKER_USERNAME}/${IMAGE_NAME}:latest \
        .
    
    echo ""
    echo "📤 Lade Images hoch..."
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
    
    echo ""
    echo "✅ Image erfolgreich gebaut und hochgeladen!"
    echo "   Verfügbar für: AMD64 (x86_64)"
    echo "   Tags: ${VERSION} und latest"
    
elif [ "$BUILD_TYPE" = "3" ]; then
    echo ""
    echo "🏗️  Baue Image für ARM64..."
    docker build --platform linux/arm64 \
        -t ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION} \
        -t ${DOCKER_USERNAME}/${IMAGE_NAME}:latest \
        .
    
    echo ""
    echo "📤 Lade Images hoch..."
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
    
    echo ""
    echo "✅ Image erfolgreich gebaut und hochgeladen!"
    echo "   Verfügbar für: ARM64"
    echo "   Tags: ${VERSION} und latest"
else
    echo "❌ Ungültige Auswahl!"
    exit 1
fi

echo ""
echo "🌐 Image verfügbar auf: https://hub.docker.com/r/${DOCKER_USERNAME}/${IMAGE_NAME}"
echo ""
