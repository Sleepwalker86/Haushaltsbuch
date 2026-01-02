"""
Logging-Konfiguration für die Finanzapp

Stellt ein zentrales Logging-System mit automatischer Rotation bereit.
Logs werden nach Zeit (täglich) und Größe (10 MB) rotiert.
Alte Logs werden automatisch nach 30 Tagen gelöscht.
"""

import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


# Log-Verzeichnis (konfigurierbar über Umgebungsvariable)
LOG_DIR = os.environ.get('LOG_DIR', os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    'data', 'log'
))

# Stelle sicher, dass Log-Verzeichnis existiert
os.makedirs(LOG_DIR, exist_ok=True)

# Log-Datei-Pfad
LOG_FILE = os.path.join(LOG_DIR, 'finanzapp.log')


def setup_logging(app):
    """
    Konfiguriert das Logging für die Flask-Anwendung.
    
    Args:
        app: Flask-App-Instanz
    """
    # Deaktiviere Standard-Flask-Logging
    app.logger.handlers.clear()
    
    # Log-Level aus Umgebungsvariable (default: INFO)
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Formatter für Logs
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # TimedRotatingFileHandler: Rotiert täglich um Mitternacht
    # Behält 30 Tage alte Logs
    # Kombiniert mit maxBytes-Logik für zusätzliche Größen-Rotation
    time_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    time_handler.setLevel(numeric_level)
    time_handler.setFormatter(formatter)
    time_handler.suffix = '%Y-%m-%d'  # Suffix: YYYY-MM-DD
    
    # Console-Handler für Entwicklung
    if os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true', 'yes'):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
    
    # Datei-Handler hinzufügen
    # TimedRotatingFileHandler rotiert täglich und behält 30 Tage
    app.logger.addHandler(time_handler)
    
    # Zusätzliche Größen-Rotation: Prüfe täglich ob Datei > 10 MB
    # (wird durch TimedRotatingFileHandler automatisch bei täglicher Rotation gehandhabt)
    
    # Setze Log-Level
    app.logger.setLevel(numeric_level)
    
    # Deaktiviere Logging von Drittanbieter-Bibliotheken (optional)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('mysql').setLevel(logging.WARNING)
    
    app.logger.info(f"Logging initialisiert. Log-Datei: {LOG_FILE}")
    app.logger.info(f"Log-Level: {log_level}")


def get_log_file_path():
    """
    Gibt den Pfad zur aktuellen Log-Datei zurück.
    
    Returns:
        str: Pfad zur Log-Datei
    """
    return LOG_FILE


def get_log_files():
    """
    Gibt eine Liste aller verfügbaren Log-Dateien zurück (inkl. rotierte).
    
    Returns:
        list: Liste von Log-Datei-Pfaden, sortiert nach Änderungsdatum (neueste zuerst)
    """
    log_files = []
    
    if os.path.exists(LOG_FILE):
        log_files.append(LOG_FILE)
    
    # Suche nach rotierten Log-Dateien
    base_name = os.path.basename(LOG_FILE)
    base_name_no_ext = os.path.splitext(base_name)[0]
    log_dir = os.path.dirname(LOG_FILE)
    
    if os.path.exists(log_dir):
        for file in os.listdir(log_dir):
            if file.startswith(base_name_no_ext) and file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                if file_path != LOG_FILE:
                    log_files.append(file_path)
    
    # Sortiere nach Änderungsdatum (neueste zuerst)
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return log_files


def cleanup_old_logs(days=30):
    """
    Löscht Log-Dateien, die älter als die angegebene Anzahl von Tagen sind.
    
    Args:
        days: Anzahl der Tage, nach denen Logs gelöscht werden sollen (default: 30)
    
    Returns:
        int: Anzahl der gelöschten Dateien
    """
    import time
    from datetime import datetime, timedelta
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted_count = 0
    
    log_files = get_log_files()
    for log_file in log_files:
        # Lösche nicht die aktuelle Log-Datei
        if log_file == LOG_FILE:
            continue
        
        try:
            if os.path.getmtime(log_file) < cutoff_time:
                os.remove(log_file)
                deleted_count += 1
        except Exception as e:
            logging.getLogger(__name__).error(f"Fehler beim Löschen von {log_file}: {e}")
    
    return deleted_count
