"""
CSRF-Schutz für Flask-Anwendung

Dieses Modul stellt Funktionen für die Generierung und Validierung von
CSRF-Tokens bereit. CSRF-Tokens sind an die Session gebunden und schützen
vor Cross-Site Request Forgery Angriffen.
"""

import secrets
from functools import wraps
from flask import session, request, abort, current_app


# Session-Key für CSRF-Token
CSRF_TOKEN_KEY = '_csrf_token'


def generate_csrf_token():
    """
    Generiert ein kryptografisch sicheres CSRF-Token.
    
    Das Token wird in der Session gespeichert und ist an die aktuelle
    Session gebunden. Bei jeder neuen Session wird ein neues Token erzeugt.
    
    Returns:
        str: Ein hexadezimales Token (32 Bytes = 64 Zeichen)
    """
    # Stelle sicher, dass die Session permanent ist
    if not hasattr(session, 'permanent') or not session.permanent:
        session.permanent = True
    
    if CSRF_TOKEN_KEY not in session:
        # Generiere kryptografisch sicheres Token (32 Bytes = 256 Bit)
        session[CSRF_TOKEN_KEY] = secrets.token_hex(32)
        # Session explizit als geändert markieren, damit sie gespeichert wird
        session.modified = True
    
    return session[CSRF_TOKEN_KEY]


def get_csrf_token():
    """
    Gibt das aktuelle CSRF-Token zurück oder generiert ein neues.
    
    Returns:
        str: Das CSRF-Token für die aktuelle Session
    """
    return generate_csrf_token()


def validate_csrf_token(token=None):
    """
    Validiert ein CSRF-Token gegen das in der Session gespeicherte Token.
    
    Args:
        token: Das zu validierende Token (optional, wird aus request.form geholt)
    
    Returns:
        bool: True wenn das Token gültig ist, False sonst
    """
    if token is None:
        # Token aus Formular oder Header holen
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    
    if not token:
        # Debug: Zeige alle verfügbaren Formularfelder
        form_keys = list(request.form.keys()) if hasattr(request, 'form') else []
        current_app.logger.error(f"CSRF-Token-Validierung: Kein Token im Request gefunden. Form-Felder: {form_keys}")
        return False
    
    session_token = session.get(CSRF_TOKEN_KEY)
    if not session_token:
        # Wenn kein Token in Session, generiere eines (für Debugging)
        current_app.logger.error(f"CSRF-Token-Validierung: Kein Token in Session gefunden. Session-Keys: {list(session.keys())}")
        # Versuche Token zu generieren (für nächsten Request)
        generate_csrf_token()
        return False
    
    # Verwende secrets.compare_digest für zeitkonstante Vergleiche
    # (schützt vor Timing-Angriffen)
    is_valid = secrets.compare_digest(token, session_token)
    if not is_valid:
        current_app.logger.error(
            f"CSRF-Token-Validierung: Token stimmt nicht überein.\n"
            f"  Session-Token (erste 20 Zeichen): {session_token[:20]}...\n"
            f"  Request-Token (erste 20 Zeichen): {token[:20]}...\n"
            f"  Token-Längen: Session={len(session_token)}, Request={len(token)}"
        )
    return is_valid


def csrf_protect(f):
    """
    Decorator zum Schutz von Routes vor CSRF-Angriffen.
    
    Dieser Decorator prüft bei POST, PUT, PATCH und DELETE Requests,
    ob ein gültiges CSRF-Token vorhanden ist. Fehlt das Token oder ist
    es ungültig, wird der Request mit HTTP 403 Forbidden abgelehnt.
    
    Usage:
        @bp.route("/example", methods=["POST"])
        @csrf_protect
        def example():
            ...
    
    Args:
        f: Die zu schützende Route-Funktion
    
    Returns:
        Die dekorierte Funktion mit CSRF-Schutz
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Nur bei zustandsverändernden HTTP-Methoden prüfen
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            # Stelle sicher, dass Session permanent ist (wichtig für Persistenz)
            if not hasattr(session, 'permanent') or not session.permanent:
                session.permanent = True
            
            # Debug: Zeige alle Formularfelder
            if current_app.debug:
                current_app.logger.debug(f"CSRF-Validierung: Form-Daten: {list(request.form.keys())}")
                current_app.logger.debug(f"CSRF-Validierung: Session-Token vorhanden: {CSRF_TOKEN_KEY in session}")
                current_app.logger.debug(f"CSRF-Validierung: Session-Keys: {list(session.keys())}")
            
            if not validate_csrf_token():
                # Detaillierte Fehlerausgabe
                form_token = request.form.get('csrf_token', 'FEHLT')
                session_token = session.get(CSRF_TOKEN_KEY, 'FEHLT')
                current_app.logger.error(
                    f"CSRF-Token-Validierung fehlgeschlagen für {request.method} {request.path} "
                    f"von {request.remote_addr}.\n"
                    f"  Form-Felder: {list(request.form.keys())}\n"
                    f"  Token im Formular: {form_token[:30] if isinstance(form_token, str) else form_token}\n"
                    f"  Token in Session: {session_token[:30] if isinstance(session_token, str) else session_token}\n"
                    f"  Session permanent: {session.permanent if hasattr(session, 'permanent') else 'N/A'}"
                )
                abort(403, description="CSRF-Token fehlt oder ist ungültig. Bitte laden Sie die Seite neu und versuchen Sie es erneut.")
        
        return f(*args, **kwargs)
    
    return decorated_function


def rotate_csrf_token():
    """
    Rotiert das CSRF-Token (erzeugt ein neues Token).
    
    Dies kann nach kritischen Operationen aufgerufen werden, um
    Replay-Angriffe zu erschweren. Das alte Token wird ungültig.
    """
    session.pop(CSRF_TOKEN_KEY, None)
    return generate_csrf_token()
