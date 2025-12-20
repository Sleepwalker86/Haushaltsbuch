FROM python:3.11-slim

# Arbeitsverzeichnis setzen
WORKDIR /app

# System-Abhängigkeiten installieren
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungsdateien kopieren
COPY . .

# Verzeichnisse für Uploads erstellen
RUN mkdir -p /app/import /app/image

# Port freigeben
EXPOSE 5001

# Entrypoint-Script ausführbar machen
RUN chmod +x /app/docker-entrypoint.sh

# Entrypoint setzen
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Standard-Command
CMD ["python", "app.py"]
