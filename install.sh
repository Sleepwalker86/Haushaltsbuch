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
# SUDO PRÜFUNG & INSTALLATION
# -----------------------------
if ! command -v sudo &> /dev/null; then
    echo "⚠️  sudo ist nicht installiert. Installiere sudo..."
    apt update
    apt install -y sudo || {
        echo "❌ Fehler: sudo konnte nicht installiert werden."
        echo "   Bitte installieren Sie sudo manuell mit: apt install sudo"
        exit 1
    }
    echo "✅ sudo wurde erfolgreich installiert."
fi

# -----------------------------
# SYSTEM UPDATE
# -----------------------------
echo "📦 Systempakete aktualisieren..."
apt update

# -----------------------------
# DATENBANK-AUSWAHL
# -----------------------------
echo ""
echo "🗄️  Datenbank-Konfiguration"
echo "Möchten Sie eine externe oder interne Datenbank verwenden?"
read -p "Externe Datenbank verwenden? (j/n) [n]: " USE_EXTERNAL_DB
USE_EXTERNAL_DB=${USE_EXTERNAL_DB:-n}

if [[ "$USE_EXTERNAL_DB" =~ ^[JjYy]$ ]]; then
    USE_INTERNAL_DB=false
    echo "✅ Externe Datenbank wird verwendet."
else
    USE_INTERNAL_DB=true
    echo "✅ Interne Datenbank wird installiert und konfiguriert."
fi

# -----------------------------
# PAKETE
# -----------------------------
echo "📦 Installiere benötigte Pakete..."
if [ "$USE_INTERNAL_DB" = true ]; then
    # Installiere MariaDB Server für interne Datenbank
    apt install -y \
      python3 \
      python3-venv \
      python3-pip \
      mariadb-server \
      mariadb-client \
      ca-certificates \
      curl \
      git \
      sudo
else
    # Nur Client für externe Datenbank
    apt install -y \
      python3 \
      python3-venv \
      python3-pip \
      mariadb-client \
      ca-certificates \
      curl \
      git \
      sudo
fi

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
    echo "🔄 App-Verzeichnis existiert bereits – aktualisiere Repo als ${APP_USER}..."
    # Sicherstellen, dass der Besitzer korrekt ist, bevor git als finanzapp läuft
    chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
    # Dubious-ownership-Check umgehen, indem wir das Verzeichnis für den User als sicher markieren
    sudo -u "$APP_USER" git config --global --add safe.directory "$APP_DIR" || true
    sudo -u "$APP_USER" git -C "$APP_DIR" reset --hard
    sudo -u "$APP_USER" git -C "$APP_DIR" pull
else
    echo "📁 App-Verzeichnis existiert noch nicht, klone Repo..."
    rm -rf "$APP_DIR"
    mkdir -p "$APP_DIR"
    chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
    sudo -u "$APP_USER" git clone "$GIT_REPO" "$APP_DIR"
fi

# Unterordner erstellen
mkdir -p "$APP_DIR/import" "$APP_DIR/imported"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# -----------------------------
# INTERNE DATENBANK SETUP
# -----------------------------
if [ "$USE_INTERNAL_DB" = true ]; then
    echo "🗄️  Konfiguriere interne MariaDB-Datenbank..."
    
    # Stelle sicher, dass MariaDB läuft
    systemctl start mariadb
    systemctl enable mariadb
    
    # Warte kurz, damit MariaDB vollständig gestartet ist
    sleep 3
    
    # Prüfe, ob MariaDB bereits konfiguriert ist
    MYSQL_ROOT_PASS=""
    if mysql -u root -e "SELECT 1" &>/dev/null 2>&1; then
        # MariaDB hat noch kein Root-Passwort
        echo "🔐 Setze MariaDB Root-Passwort..."
        read -sp "MariaDB Root-Passwort setzen (Enter für automatische Generierung): " MYSQL_ROOT_PASS
        echo
        if [ -z "$MYSQL_ROOT_PASS" ]; then
            MYSQL_ROOT_PASS=$(openssl rand -base64 32)
            echo "⚠️  Kein Passwort eingegeben. Generiertes Passwort: $MYSQL_ROOT_PASS"
            echo "⚠️  Bitte notieren Sie sich dieses Passwort!"
        fi
        
        # Setze Root-Passwort
        mysql -u root <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '$MYSQL_ROOT_PASS';
FLUSH PRIVILEGES;
EOF
    else
        # MariaDB hat bereits ein Root-Passwort
        echo "🔐 MariaDB Root-Passwort existiert bereits."
        read -sp "Bitte geben Sie das bestehende Root-Passwort ein: " MYSQL_ROOT_PASS
        echo
        # Teste ob das Passwort korrekt ist
        if ! mysql -u root -p"$MYSQL_ROOT_PASS" -e "SELECT 1" &>/dev/null 2>&1; then
            echo "❌ Falsches Root-Passwort! Bitte erneut versuchen."
            exit 1
        fi
    fi
    
    # Sichere MariaDB-Installation durchführen
    echo "🔒 Führe mysql_secure_installation durch..."
    mysql -u root ${MYSQL_ROOT_PASS:+-p"$MYSQL_ROOT_PASS"} <<EOF
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOF
    
    # Datenbank und User für die App erstellen
    echo "📊 Erstelle Datenbank und Benutzer für die App..."
    read -p "Datenbank-Name [Haushaltsbuch]: " DB_NAME
    DB_NAME=${DB_NAME:-Haushaltsbuch}
    
    read -p "Datenbank-Benutzer [finanzapp_user]: " DB_USER
    DB_USER=${DB_USER:-finanzapp_user}
    
    read -sp "Datenbank-Passwort für $DB_USER: " DB_PASS
    echo
    if [ -z "$DB_PASS" ]; then
        DB_PASS=$(openssl rand -base64 24)
        echo "⚠️  Kein Passwort eingegeben. Generiertes Passwort: $DB_PASS"
    fi
    
    # Erstelle Datenbank und User
    mysql -u root ${MYSQL_ROOT_PASS:+-p"$MYSQL_ROOT_PASS"} <<EOF
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF
    
    DB_HOST="127.0.0.1"
    echo "✅ Interne Datenbank konfiguriert: $DB_NAME auf $DB_HOST"
fi

# -----------------------------
# PYTHON VENV & ABHÄNGIGKEITEN
# -----------------------------
echo "🐍 Richte Python-virtualenv im App-Verzeichnis ein..."
if [ ! -d "$APP_DIR/venv" ]; then
  sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
fi

echo "🐍 Installiere Python-Abhängigkeiten in venv..."
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip

# Wenn eine requirements.txt im Repo liegt, immer diese installieren (auch bei Updates),
# damit neue Abhängigkeiten automatisch nachgezogen werden.
if [ -f "$APP_DIR/requirements.txt" ]; then
  echo "🐍 Installiere Python-Abhängigkeiten aus requirements.txt..."
  sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
else
  echo "⚠️  requirements.txt nicht gefunden, installiere Minimal-Set direkt..."
  sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install \
    flask \
    mysql-connector-python \
    pandas \
    python-dateutil
fi

# -----------------------------
# CONFIG.JSON
# -----------------------------
CONFIG_FILE="$APP_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚙️ config.json existiert nicht, erstelle neue..."
    
    if [ "$USE_INTERNAL_DB" = true ]; then
        # Für interne DB wurden die Werte bereits oben eingegeben
        echo "✅ Verwende bereits konfigurierte interne Datenbank-Einstellungen..."
        # DB_HOST, DB_USER, DB_PASS, DB_NAME sind bereits gesetzt
    else
        # Für externe DB müssen die Werte eingegeben werden
        read -p "DB Host [192.168.10.100]: " DB_HOST
        DB_HOST=${DB_HOST:-192.168.10.100}

        read -p "DB User [db_user]: " DB_USER
        DB_USER=${DB_USER:-db_user}

        read -sp "DB Password [1234]: " DB_PASS
        echo
        DB_PASS=${DB_PASS:-1234}

        read -p "DB Name [Haushaltsbuch]: " DB_NAME
        DB_NAME=${DB_NAME:-Haushaltsbuch}
    fi

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
if [ "$USE_INTERNAL_DB" = true ]; then
    IMPORT_AFTER="network.target mariadb.service"
else
    IMPORT_AFTER="network.target"
fi
cat > "$IMPORT_SERVICE_FILE" <<EOF
[Unit]
Description=Finanz App CSV-Import
After=${IMPORT_AFTER}

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
