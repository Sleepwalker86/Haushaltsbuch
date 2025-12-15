#!/bin/bash
set -e

APP_NAME="finanzapp"
APP_DIR="/opt/finanzapp"
APP_USER="finanzapp"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
IMPORT_SERVICE_FILE="/etc/systemd/system/${APP_NAME}-import.service"
IMPORT_TIMER_FILE="/etc/systemd/system/${APP_NAME}-import.timer"

echo "🧹 Deinstallation von ${APP_NAME} startet..."

# -----------------------------
# ROOT CHECK
# -----------------------------
if [ "$EUID" -ne 0 ]; then
  echo "❌ Bitte als root ausführen!"
  exit 1
fi

# -----------------------------
# SERVICES STOPPEN / DEAKTIVIEREN
# -----------------------------
echo "⏹ Stoppe Services und Timer (falls aktiv)..."
systemctl stop "${APP_NAME}-import.timer" 2>/dev/null || true
systemctl stop "${APP_NAME}-import.service" 2>/dev/null || true
systemctl stop "${APP_NAME}" 2>/dev/null || true

echo "🚫 Deaktiviere Services und Timer..."
systemctl disable "${APP_NAME}-import.timer" 2>/dev/null || true
systemctl disable "${APP_NAME}-import.service" 2>/dev/null || true
systemctl disable "${APP_NAME}" 2>/dev/null || true

# -----------------------------
# SYSTEMD-UNITS LÖSCHEN
# -----------------------------
echo "🗑  Entferne systemd-Units..."
rm -f "$SERVICE_FILE" "$IMPORT_SERVICE_FILE" "$IMPORT_TIMER_FILE"

echo "🔄 systemd neu laden..."
systemctl daemon-reload
systemctl reset-failed || true

# -----------------------------
# APP-VERZEICHNIS LÖSCHEN
# -----------------------------
if [ -d "$APP_DIR" ]; then
  echo "🗑  Entferne App-Verzeichnis ${APP_DIR}..."
  rm -rf "$APP_DIR"
else
  echo "ℹ️  App-Verzeichnis ${APP_DIR} existiert nicht, überspringe."
fi

# -----------------------------
# USER OPTIONAL LÖSCHEN
# -----------------------------
if id "$APP_USER" &>/dev/null; then
  read -p "Soll der Benutzer '${APP_USER}' ebenfalls gelöscht werden? [y/N]: " DEL_USER
  if [[ "$DEL_USER" =~ ^[Yy]$ ]]; then
    echo "👤 Lösche Benutzer ${APP_USER}..."
    userdel "$APP_USER" 2>/dev/null || echo "ℹ️  Konnte Benutzer nicht löschen (ggf. noch Prozesse aktiv)."
  else
    echo "ℹ️  Benutzer ${APP_USER} bleibt bestehen."
  fi
else
  echo "ℹ️  Benutzer ${APP_USER} existiert nicht, überspringe."
fi

echo "✅ Deinstallation abgeschlossen."


