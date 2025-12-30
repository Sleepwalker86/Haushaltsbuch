"""Hauptanwendung - Flask App Initialisierung."""
import os
from flask import Flask, render_template, session, request, g

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

# Session-Konfiguration für sichere, serverseitige Sessions
# Sessions werden als signierte Cookies gespeichert (serverseitig)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Verhindert JavaScript-Zugriff
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Schutz vor CSRF (Lax erlaubt GET-Requests von anderen Sites)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # Nur über HTTPS in Produktion
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 Stunden (in Sekunden)
app.config['SESSION_COOKIE_NAME'] = 'finanzapp_session'  # Eindeutiger Cookie-Name


@app.before_request
def make_session_permanent():
    """Stellt sicher, dass die Session permanent ist und richtig funktioniert."""
    # Stelle sicher, dass die Session permanent ist
    # Dies ist wichtig, damit CSRF-Tokens zwischen Requests persistiert werden
    session.permanent = True
    # Stelle sicher, dass Session gespeichert wird
    session.modified = True


@app.template_global()
def get_csrf_token_value():
    """Template-Funktion um CSRF-Token direkt in Templates zu holen."""
    from utils.csrf import get_csrf_token
    return get_csrf_token()


@app.context_processor
def inject_config():
    """Injiziert Konfiguration und CSRF-Token in alle Templates."""
    try:
        config = load_config()
        paperless_enabled = config.get("PAPERLESS", {}).get("enabled", False)
    except Exception:
        paperless_enabled = False
    
    # CSRF-Token für alle Templates verfügbar machen
    # WICHTIG: Token wird hier generiert und in Session gespeichert
    from utils.csrf import get_csrf_token, CSRF_TOKEN_KEY
    try:
        # Stelle sicher, dass Session permanent ist
        session.permanent = True
        # Generiere Token (wird in Session gespeichert)
        csrf_token_value = get_csrf_token()
        # Debug: Prüfe ob Token wirklich generiert wurde
        if not csrf_token_value:
            import logging
            logging.warning("CSRF-Token ist leer nach get_csrf_token()")
        else:
            # Stelle sicher, dass Session gespeichert wird
            session.modified = True
    except Exception as e:
        # Fallback falls Session-Probleme auftreten
        import logging
        logging.error(f"Fehler beim Generieren des CSRF-Tokens: {e}")
        csrf_token_value = ""
    
    return {
        "paperless_enabled": paperless_enabled,
        "csrf_token": csrf_token_value,  # Verfügbar als {{ csrf_token }} in Templates
        "csrf_token_value": csrf_token_value  # Alternative Variable für Makros (vermeidet Namenskonflikt)
    }


@app.errorhandler(403)
def forbidden(error):
    """Custom Error-Handler für 403 Forbidden (CSRF-Fehler)."""
    return render_template('error.html', 
                         error_code=403,
                         error_message="Zugriff verweigert",
                         error_description="CSRF-Token fehlt oder ist ungültig. Bitte laden Sie die Seite neu und versuchen Sie es erneut."), 403


# Blueprints registrieren
from routes.dashboard import bp as dashboard_bp
from routes.actions import bp as actions_bp
from routes.settings import bp as settings_bp
from routes.upload import bp as upload_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(actions_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(upload_bp)


# Debug-Route für CSRF-Token (nur im Debug-Modus verfügbar)
if os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes"):
    from utils.csrf import csrf_protect
    @app.route("/debug/csrf", methods=["GET", "POST"])
    @csrf_protect
    def debug_csrf():
        """Debug-Route um CSRF-Token-Status zu prüfen (nur im Debug-Modus)."""
        from utils.csrf import get_csrf_token, CSRF_TOKEN_KEY
        token = get_csrf_token()
        session_token = session.get(CSRF_TOKEN_KEY)
        form_token = request.form.get('csrf_token', 'NICHT GEFUNDEN') if request.method == 'POST' else 'N/A (GET Request)'
        
        debug_info = {
            "session_id": session.get('_id', 'Keine Session-ID'),
            "session_keys": list(session.keys()),
            "csrf_token_in_session": session_token is not None,
            "csrf_token_value": session_token[:20] + "..." if session_token else "KEIN TOKEN",
            "csrf_token_from_get": token[:20] + "..." if token else "KEIN TOKEN",
            "csrf_token_from_form": form_token[:20] + "..." if isinstance(form_token, str) and len(form_token) > 20 else form_token,
            "session_permanent": session.permanent if hasattr(session, 'permanent') else 'N/A',
            "request_method": request.method,
            "form_keys": list(request.form.keys()) if request.method == 'POST' else []
        }
        
        return f"""
        <h1>CSRF Debug Information</h1>
        <pre>{debug_info}</pre>
        <hr>
        <h2>Test-Formular</h2>
        <form method="post">
            {{% from "macros.html" import csrf_token %}}
            {{ csrf_token() }}
            <button type="submit">Test POST</button>
        </form>
        """


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.config['DEBUG'] = debug # Debug-Modus aktivieren für bessere Fehlermeldungen
    app.run(debug=debug, host="0.0.0.0", port=5001)
