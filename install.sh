#!/bin/bash

set -e

APP_NAME="finanzapp"
APP_DIR="/opt/finanzapp"
APP_USER="finanzapp"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

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
#echo "📦 System aktualisieren..."
#apt update

# -----------------------------
# PAKETE
# -----------------------------
echo "📦 Installiere benötigte Pakete..."
apt install -y \
  python3 \
  python3-pip \
  python3-mysql.connector \
  mariadb-client \
  ca-certificates \
  curl

# -----------------------------
# USER
# -----------------------------
if ! id "$APP_USER" &>/dev/null; then
  echo "👤 Erstelle User ${APP_USER}..."
  useradd -r -s /bin/false "$APP_USER"
fi

# -----------------------------
# APP ORDNER
# -----------------------------
echo "📁 Erstelle App-Verzeichnis..."
mkdir -p "$APP_DIR"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

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
