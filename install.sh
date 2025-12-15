#!/bin/bash
set -e

APP_NAME="finanzapp"
APP_DIR="/opt/finanzapp"
APP_USER="finanzapp"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
GIT_REPO="https://github.com/Sleepwalker86/Haushaltsbuch.git"

echo "🚀 Installation von ${APP_NAME} startet..."

# -----------------------------
# ROOT CHECK
# -----------------------------
if [ "$EUID" -ne 0 ]; then
  echo "❌ Bitte als root ausführen!"
  exit 1
fi

# -----------------------------
# SYSTEM UPDATE
# -----------------------------
echo "📦 Systempakete aktualisieren..."
apt update

# -----------------------------
# PAKETE
# -----------------------------
echo "📦 Installiere benötigte Pakete..."
apt install -y \
  python3 \
  python3-pip \
  mariadb-client \
  ca-certificates \
  curl \
  git

# -----------------------------
# USER
# -----------------------------
if ! id "$APP_USER" &>/dev/null; then
  echo "👤 Erstelle User ${APP_USER}..."
  useradd -r -s /bin/false "$APP_USER"
fi

# -----------------------------
# APP ORDNER & GIT
# -----------------------------
if [ -d "$APP_DIR/.git" ]; then
    echo "🔄 App existiert bereits – aktualisiere mit git pull als ${APP_USER}..."
    sudo -u "$APP_USER" git -C "$APP_DIR" reset --hard
    sudo -u "$APP_USER" git -C "$APP_DIR" pull
else
    echo "📁 Erstelle App-Verzeichnis und klone Repo..."
    mkdir -p "$APP_DIR"
    chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
    sudo -u "$APP_USER" git clone "$GIT_REPO" "$APP_DIR"
fi

# Unterordner erstellen
mkdir -p "$APP_DIR/import" "$APP_DIR/imported"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# -----------------------------
# CONFIG.JSON
# -----------------------------
CONFIG_FILE="$APP_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚙️ config.json existiert nicht, erstelle neue..."
    
    read -p "DB Host [192.168.10.99]: " DB_HOST
    DB_HOST=${DB_HOST:-192.168.10.99}

    read -p "DB User [smo]: " DB_USER
    DB_USER=${DB_USER:-smo}

    read -sp "DB Password [1234]: " DB_PASS
    echo
    DB_PASS=${DB_PASS:-1234}

    read -p "DB Name [Haushaltsbuch]: " DB_NAME
    DB_NAME=${DB_NAME:-Haushaltsbuch}

    cat > "$CONFIG_FILE" <<EOF
{
  "DB_CONFIG": {
    "host": "$DB_HOST",
    "user": "$DB_USER",
    "password": "$DB_PASS",
    "database": "$DB_NAME"
  }
}
EOF

    chown "$APP_USER":"$APP_USER" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
else
    echo "✅ config.json existiert bereits, überspringe Erstellung."
fi

# -----------------------------
# PYTHON ABHÄNGIGKEITEN
# -----------------------------
echo "🐍 Installiere Python-Abhängigkeiten global..."
pip3 install --upgrade pip
pip3 install flask mysql-connector-python pandas python-dateutil

# -----------------------------
# SYSTEMD SERVICE
# -----------------------------
echo "⚙️ Erstelle systemd Service..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Finanz App
After=network.target mariadb.service

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 ${APP_DIR}/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# -----------------------------
# RECHTE
# -----------------------------
chown root:root "$SERVICE_FILE"
chmod 644 "$SERVICE_FILE"

# -----------------------------
# SYSTEMD AKTUALISIEREN
# -----------------------------
echo "🔄 systemd neu laden..."
systemctl daemon-reload
systemctl enable ${APP_NAME}
systemctl restart ${APP_NAME}

# -----------------------------
# STATUS
# -----------------------------
echo "✅ Installation abgeschlossen!"
echo ""
systemctl status ${APP_NAME} --no-pager
