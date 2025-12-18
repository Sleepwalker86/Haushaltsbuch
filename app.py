"""Hauptanwendung - Flask App Initialisierung."""
import os
from flask import Flask

from utils.helpers import load_config

app = Flask(__name__)
# Secret Key aus config.json lesen, Fallback für Entwicklung
try:
    config = load_config()
    app.secret_key = config.get("SECRET_KEY", "change-me-please")
except Exception:
    app.secret_key = "change-me-please"

if app.secret_key == "change-me-please":
    import warnings
    warnings.warn(
        "⚠️  WARNUNG: Secret Key verwendet Standard-Wert! "
        "Für Produktion bitte SECRET_KEY in config.json setzen.",
        UserWarning
    )


@app.context_processor
def inject_config():
    try:
        config = load_config()
        paperless_enabled = config.get("PAPERLESS", {}).get("enabled", False)
    except Exception:
        paperless_enabled = False
    return {"paperless_enabled": paperless_enabled}


# Blueprints registrieren
from routes.dashboard import bp as dashboard_bp
from routes.actions import bp as actions_bp
from routes.settings import bp as settings_bp
from routes.upload import bp as upload_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(actions_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(upload_bp)


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.config['DEBUG'] = debug # Debug-Modus aktivieren für bessere Fehlermeldungen
    app.run(debug=debug, host="0.0.0.0", port=5001)
