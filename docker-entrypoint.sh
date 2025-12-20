#!/bin/bash
set -e

echo "🚀 Starte Finanzapp Container..."

# Prüfe ob externe DB verwendet werden soll
if [ -n "${DB_HOST}" ] && [ "${DB_HOST}" != "db" ]; then
    # Externe Datenbank
    echo "ℹ️  Verwende externe Datenbank: ${DB_HOST}"
    
    # Validiere erforderliche Parameter
    if [ -z "${DB_USER}" ] || [ -z "${DB_PASSWORD}" ] || [ -z "${DB_NAME}" ]; then
        echo "❌ FEHLER: Für externe Datenbank müssen folgende Parameter gesetzt sein:"
        echo "   DB_HOST=${DB_HOST:-<FEHLT>}"
        echo "   DB_USER=${DB_USER:-<FEHLT>}"
        echo "   DB_PASSWORD=${DB_PASSWORD:-<FEHLT>}"
        echo "   DB_NAME=${DB_NAME:-<FEHLT>}"
        echo ""
        echo "   Bitte setzen Sie diese in der .env Datei!"
        exit 1
    fi
    
    # Teste Verbindung zur externen DB
    echo "🔍 Teste Verbindung zur externen Datenbank..."
    echo "   Host: ${DB_HOST}"
    echo "   User: ${DB_USER}"
    echo "   Database: ${DB_NAME}"
    
    # Teste Netzwerk-Erreichbarkeit (Port 3306)
    echo "   Prüfe Netzwerk-Erreichbarkeit..."
    if command -v nc >/dev/null 2>&1; then
        if nc -z -w 5 "${DB_HOST}" 3306 2>/dev/null; then
            echo "   ✅ Port 3306 ist erreichbar"
        else
            echo "   ⚠️  Port 3306 ist NICHT erreichbar!"
            echo "   Bitte prüfen Sie:"
            echo "   - Ist die IP-Adresse korrekt? (${DB_HOST})"
            echo "   - Ist die Firewall konfiguriert?"
            echo "   - Läuft MySQL auf Port 3306?"
        fi
    fi
    
    # Teste MySQL-Verbindung mit detaillierter Fehlerausgabe
    max_attempts=5
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        echo "   Versuche Verbindung... (Versuch $attempt/$max_attempts)"
        
        # Teste Verbindung direkt mit Datenbankname
        # Temporär set -e deaktivieren für Fehlerbehandlung
        set +e
        ERROR_OUTPUT=$(python3 -c "
import mysql.connector
import sys
import time

try:
    conn = mysql.connector.connect(
        host='${DB_HOST}',
        user='${DB_USER}',
        password='${DB_PASSWORD}',
        database='${DB_NAME}',
        connection_timeout=5,
        autocommit=True,
        buffered=True
    )
    cursor = conn.cursor(buffered=True)
    cursor.execute('SELECT 1')
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    time.sleep(0.1)
    print('SUCCESS')
    sys.exit(0)
except mysql.connector.Error as e:
    error_msg = str(e)
    error_code = e.errno if hasattr(e, 'errno') else 'unknown'
    if 'Unknown database' in error_msg or '1049' in str(error_code):
        print(f'DATENBANK EXISTIERT NICHT: {error_msg} (Code: {error_code})', file=sys.stderr)
    elif 'Access denied' in error_msg or '1045' in str(error_code):
        print(f'ZUGANGSVERWEIGERT: {error_msg} (Code: {error_code})', file=sys.stderr)
    elif 'Can\\'t connect' in error_msg or 'Connection refused' in error_msg:
        print(f'VERBINDUNG FEHLGESCHLAGEN: {error_msg} (Code: {error_code})', file=sys.stderr)
    else:
        print(f'MYSQL FEHLER: {error_msg} (Code: {error_code})', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    import traceback
    print(f'UNBEKANNTER FEHLER: {e}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
" 2>&1)
        CONNECTION_STATUS=$?
        # Fehlerausgabe sofort anzeigen, auch wenn set -e aktiv ist
        if [ $CONNECTION_STATUS -ne 0 ]; then
            echo "   ❌ Fehler beim Datenbankzugriff: ${ERROR_OUTPUT}" >&2
        fi
        set -e
        
        if [ $CONNECTION_STATUS -eq 0 ]; then
            echo "✅ Verbindung zur externen Datenbank erfolgreich"
            break
        else
            # Fehlerausgabe immer anzeigen
            echo "   ❌ Fehler beim Datenbankzugriff:"
            echo "   ${ERROR_OUTPUT}" | sed 's/^/      /'
            
            if [ $attempt -ge $max_attempts ]; then
                echo ""
                echo "❌ Konnte nach $max_attempts Versuchen nicht zur externen Datenbank verbinden!"
                echo ""
                echo "Mögliche Ursachen:"
                echo "   1. Zugangsdaten falsch: Benutzer/Passwort/Datenbankname"
                echo "   2. Datenbank existiert nicht: '${DB_NAME}'"
                echo "   3. MySQL bind-address: MySQL erlaubt keine Remote-Verbindungen"
                echo "   4. Benutzerrechte: Benutzer hat keine Rechte für Remote-Verbindung"
                echo ""
                echo "Troubleshooting:"
                echo "   - Prüfen Sie MySQL bind-address: bind-address = 0.0.0.0 (nicht 127.0.0.1)"
                echo "   - Prüfen Sie ob Datenbank existiert: mysql -h ${DB_HOST} -u ${DB_USER} -p -e 'SHOW DATABASES;'"
                echo "   - Prüfen Sie Benutzerrechte: mysql -h ${DB_HOST} -u root -p -e \"SHOW GRANTS FOR '${DB_USER}'@'%';\""
                echo ""
                echo "   Vollständige Fehlermeldung:"
                echo "   ${ERROR_OUTPUT}" | sed 's/^/   /'
                exit 1
            fi
            echo "   Warte 3 Sekunden vor nächstem Versuch..."
            sleep 3
        fi
    done
else
    # Interne Datenbank
    echo "⏳ Warte auf MySQL Datenbank (interne DB)..."
    max_attempts=30
    attempt=0
    until python -c "import mysql.connector; mysql.connector.connect(host='${DB_HOST:-db}', user='${DB_USER}', password='${DB_PASSWORD}')" 2>/dev/null; do
      attempt=$((attempt + 1))
      if [ $attempt -ge $max_attempts ]; then
        echo "❌ MySQL ist nach $max_attempts Versuchen nicht bereit. Breche ab."
        exit 1
      fi
      echo "   MySQL ist noch nicht bereit, warte 2 Sekunden... (Versuch $attempt/$max_attempts)"
      sleep 2
    done
    echo "✅ MySQL ist bereit"
fi

# Erstelle/aktualisiere config.json immer (damit Änderungen in .env übernommen werden)
echo "⚙️  Erstelle/aktualisiere config.json..."

# PAPERLESS_ENABLED als boolean konvertieren
if [ "${PAPERLESS_ENABLED}" = "true" ] || [ "${PAPERLESS_ENABLED}" = "1" ]; then
    PAPERLESS_ENABLED_JSON="true"
else
    PAPERLESS_ENABLED_JSON="false"
fi

cat > /app/config.json <<EOF
{
  "SECRET_KEY": "${SECRET_KEY:-change-me-please}",
  "DB_CONFIG": {
    "host": "${DB_HOST:-db}",
    "user": "${DB_USER}",
    "password": "${DB_PASSWORD}",
    "database": "${DB_NAME}"
  },
  "PAPERLESS": {
    "ip": "${PAPERLESS_IP:-}",
    "token": "${PAPERLESS_TOKEN:-}",
    "document_type_id": "${PAPERLESS_DOCUMENT_TYPE_ID:-}",
    "enabled": ${PAPERLESS_ENABLED_JSON}
  }
}
EOF
echo "✅ config.json aktualisiert"

# Initialisiere Datenbank
echo "🗄️  Initialisiere Datenbank..."
if python init_db.py; then
    echo "✅ Datenbankinitialisierung erfolgreich"
else
    echo "❌ Fehler bei Datenbankinitialisierung!"
    echo "   Versuche es erneut..."
    sleep 2
    python init_db.py || {
        echo "❌ Datenbankinitialisierung fehlgeschlagen!"
        echo "   Bitte Logs prüfen: docker compose logs app"
        exit 1
    }
fi

# Starte Anwendung
echo "🎉 Starte Flask Anwendung..."
exec "$@"
