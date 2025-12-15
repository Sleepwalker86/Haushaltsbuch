#!/bin/bash
set -e

APP_NAME="finanzapp"
APP_DIR="/opt/finanzapp"
APP_USER="finanzapp"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
IMPORT_SERVICE_FILE="/etc/systemd/system/${APP_NAME}-import.service"
IMPORT_TIMER_FILE="/etc/systemd/system/${APP_NAME}-import.timer"
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
  python3-venv \
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
# PYTHON VENV & ABHÄNGIGKEITEN
# -----------------------------
echo "🐍 Richte Python-virtualenv im App-Verzeichnis ein..."
if [ ! -d "$APP_DIR/venv" ]; then
  sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
fi

echo "🐍 Installiere Python-Abhängigkeiten in venv..."
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install \
  flask \
  mysql-connector-python \
  pandas \
  python-dateutil

# -----------------------------
# CONFIG.JSON
# -----------------------------
CONFIG_FILE="$APP_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚙️ config.json existiert nicht, erstelle neue..."
    
    read -p "DB Host [192.168.10.100]: " DB_HOST
    DB_HOST=${DB_HOST:-192.168.10.100}

    read -p "DB User [db_user]: " DB_USER
    DB_USER=${DB_USER:-db_user}

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

    echo "🗄️  Initialisiere Datenbanktabellen..."
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" "$APP_DIR/init_db.py" || {
      echo "❌ Konnte Datenbanktabellen nicht anlegen. Bitte init_db.py manuell prüfen."
    }
else
    echo "✅ config.json existiert bereits, überspringe Erstellung."
fi

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
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1 FLASK_DEBUG=0

[Install]
WantedBy=multi-user.target
EOF

# Import-Service (einmaliger Lauf von import_data.py)
echo "⚙️ Erstelle systemd Import-Service..."
cat > "$IMPORT_SERVICE_FILE" <<EOF
[Unit]
Description=Finanz App CSV-Import
After=network.target

[Service]
Type=oneshot
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/import_data.py
Environment=PYTHONUNBUFFERED=1
EOF

# Timer, der den Import-Service alle 10 Minuten ausführt
echo "⚙️ Erstelle systemd Import-Timer..."
cat > "$IMPORT_TIMER_FILE" <<EOF
[Unit]
Description=Finanz App CSV-Import alle 10 Minuten

[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
Unit=${APP_NAME}-import.service

[Install]
WantedBy=timers.target
EOF

# -----------------------------
# RECHTE
# -----------------------------
chown root:root "$SERVICE_FILE" "$IMPORT_SERVICE_FILE" "$IMPORT_TIMER_FILE"
chmod 644 "$SERVICE_FILE" "$IMPORT_SERVICE_FILE" "$IMPORT_TIMER_FILE"

# -----------------------------
# SYSTEMD AKTUALISIEREN
# -----------------------------
echo "🔄 systemd neu laden..."
systemctl daemon-reload
systemctl enable ${APP_NAME}
systemctl restart ${APP_NAME}
systemctl enable ${APP_NAME}-import.timer
systemctl restart ${APP_NAME}-import.timer

# -----------------------------
# STATUS
# -----------------------------
echo "✅ Installation abgeschlossen!"
echo ""
systemctl status ${APP_NAME} --no-pager
