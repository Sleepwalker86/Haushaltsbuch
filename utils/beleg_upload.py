"""
Utility-Funktionen für Beleg-Uploads (Fotos/PDFs zu Buchungen)

Dieses Modul stellt Funktionen bereit, um Belege sicher hochzuladen,
zu speichern und zu verwalten. Belege werden in einer Ordnerstruktur
nach Jahr/Monat organisiert.
"""

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app


# Basis-Verzeichnis für Belege (konfigurierbar)
# Standard: /app/data/invoices im Container, ./data/invoices lokal
BELEG_BASE_DIR = os.environ.get('BELEG_BASE_DIR', os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    'data', 'invoices'
))

# Erlaubte Dateitypen für Belege
ALLOWED_EXTENSIONS = {
    # Bilder
    '.jpg', '.jpeg', '.png', '.webp', '.gif',
    # PDFs
    '.pdf'
}

# Maximale Dateigröße (12 MB)
MAX_FILE_SIZE = 12 * 1024 * 1024


def get_beleg_directory(datum):
    """
    Erstellt den Pfad für Belege basierend auf dem Buchungsdatum.
    
    Struktur: <BELEG_BASE_DIR>/<JAHR>/<MONAT>/
    Beispiel: /app/image/2025/12/
    
    Args:
        datum: datetime.date oder datetime Objekt mit dem Buchungsdatum
    
    Returns:
        str: Vollständiger Pfad zum Beleg-Verzeichnis
    """
    if isinstance(datum, datetime):
        year = datum.year
        month = datum.month
    else:
        year = datum.year
        month = datum.month
    
    beleg_dir = os.path.join(BELEG_BASE_DIR, str(year), f"{month:02d}")
    os.makedirs(beleg_dir, exist_ok=True)
    return beleg_dir


def is_allowed_file(filename):
    """
    Prüft, ob eine Datei einen erlaubten Dateityp hat.
    
    Args:
        filename: Name der Datei
    
    Returns:
        bool: True wenn erlaubt, False sonst
    """
    if not filename:
        return False
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS


def generate_unique_filename(original_filename, buchung_id=None):
    """
    Generiert einen eindeutigen Dateinamen für einen Beleg.
    
    Format: <UUID>_<buchung_id>_<original_name>
    Beispiel: a1b2c3d4-e5f6-7890-abcd-ef1234567890_123_rechnung.pdf
    
    Args:
        original_filename: Original-Dateiname
        buchung_id: Optional: ID der Buchung für bessere Nachverfolgbarkeit
    
    Returns:
        tuple: (sicherer Dateiname, Dateiendung)
    """
    # Sicheren Dateinamen erstellen
    safe_name = secure_filename(original_filename)
    name, ext = os.path.splitext(safe_name)
    
    # UUID für Eindeutigkeit
    unique_id = str(uuid.uuid4())
    
    # Dateiname zusammenbauen
    if buchung_id:
        new_filename = f"{unique_id}_{buchung_id}_{name}{ext}"
    else:
        new_filename = f"{unique_id}_{name}{ext}"
    
    return new_filename, ext


def save_beleg(file, datum, buchung_id=None):
    """
    Speichert einen hochgeladenen Beleg sicher.
    
    Args:
        file: Werkzeug FileStorage Objekt
        datum: datetime.date oder datetime mit Buchungsdatum
        buchung_id: Optional: ID der Buchung
    
    Returns:
        tuple: (relativer_pfad, vollständiger_pfad, fehler)
        - relativer_pfad: Relativer Pfad für Datenbank (z.B. "2025/12/beleg.pdf")
        - vollständiger_pfad: Vollständiger Pfad auf dem Dateisystem
        - fehler: Fehlermeldung oder None bei Erfolg
    """
    if not file or not file.filename:
        return None, None, "Keine Datei ausgewählt"
    
    # Dateityp prüfen
    if not is_allowed_file(file.filename):
        allowed = ', '.join(ALLOWED_EXTENSIONS)
        return None, None, f"Nur folgende Dateitypen sind erlaubt: {allowed}"
    
    # Dateigröße prüfen
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return None, None, f"Datei zu groß (max. {MAX_FILE_SIZE // (1024*1024)} MB)"
    
    try:
        # Verzeichnis erstellen
        beleg_dir = get_beleg_directory(datum)
        
        # Eindeutigen Dateinamen generieren
        filename, ext = generate_unique_filename(file.filename, buchung_id)
        
        # Vollständigen Pfad erstellen
        full_path = os.path.join(beleg_dir, filename)
        
        # Datei speichern
        file.save(full_path)
        
        # Relativen Pfad für Datenbank erstellen (ohne BELEG_BASE_DIR)
        # Format: <JAHR>/<MONAT>/<dateiname>
        if isinstance(datum, datetime):
            year = datum.year
            month = datum.month
        else:
            year = datum.year
            month = datum.month
        
        relative_path = os.path.join(str(year), f"{month:02d}", filename).replace('\\', '/')
        
        return relative_path, full_path, None
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Speichern des Belegs: {e}")
        return None, None, f"Fehler beim Speichern: {str(e)}"


def delete_beleg(beleg_pfad):
    """
    Löscht einen Beleg sicher vom Dateisystem.
    
    Args:
        beleg_pfad: Relativer Pfad (wie in Datenbank gespeichert) oder absoluter Pfad
    
    Returns:
        bool: True wenn erfolgreich gelöscht oder nicht vorhanden, False bei Fehler
    """
    if not beleg_pfad:
        return True  # Kein Beleg vorhanden, nichts zu löschen
    
    try:
        # Prüfe ob relativer oder absoluter Pfad
        if os.path.isabs(beleg_pfad):
            full_path = beleg_pfad
        else:
            # Relativer Pfad: füge BELEG_BASE_DIR hinzu
            full_path = os.path.join(BELEG_BASE_DIR, beleg_pfad)
        
        # Sicherheitsprüfung: Stelle sicher, dass Pfad innerhalb von BELEG_BASE_DIR liegt
        full_path = os.path.normpath(full_path)
        base_dir = os.path.normpath(BELEG_BASE_DIR)
        
        if not full_path.startswith(base_dir):
            current_app.logger.warning(f"Versuch, Datei außerhalb von {base_dir} zu löschen: {beleg_pfad}")
            return False
        
        # Datei löschen
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                current_app.logger.info(f"Beleg gelöscht: {full_path}")
                return True
            except OSError as e:
                current_app.logger.error(f"Fehler beim Löschen der Datei {full_path}: {e}")
                return False
        else:
            # Datei existiert nicht - das ist ok (möglicherweise bereits gelöscht)
            current_app.logger.info(f"Beleg-Datei existiert nicht (bereits gelöscht?): {full_path}")
            return True  # Datei existiert nicht, betrachten wir als Erfolg
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Belegs {beleg_pfad}: {e}", exc_info=True)
        return False


def get_beleg_path(beleg_pfad):
    """
    Gibt den vollständigen Pfad zu einem Beleg zurück.
    
    Args:
        beleg_pfad: Relativer Pfad (wie in Datenbank gespeichert)
    
    Returns:
        str: Vollständiger Pfad oder None wenn nicht gefunden
    """
    if not beleg_pfad:
        return None
    
    if os.path.isabs(beleg_pfad):
        return beleg_pfad if os.path.exists(beleg_pfad) else None
    
    full_path = os.path.join(BELEG_BASE_DIR, beleg_pfad)
    return full_path if os.path.exists(full_path) else None
