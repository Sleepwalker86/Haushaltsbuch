"""Versionsprüfung für die Anwendung."""
import requests
import re
from packaging import version


# Aktuelle Version der Anwendung
CURRENT_VERSION = "1.0.1"

# Docker Hub Repository
DOCKER_HUB_REPO = "sleepwalker86/finanzapp"


def get_latest_version_from_docker_hub():
    """
    Ruft die neueste Version vom Docker Hub ab.
    
    Returns:
        tuple: (latest_version, error_message)
        - latest_version: String mit der neuesten Version oder None bei Fehler
        - error_message: Fehlermeldung oder None bei Erfolg
    """
    try:
        # Docker Hub API v2: Tags abrufen
        url = f"https://hub.docker.com/v2/repositories/{DOCKER_HUB_REPO}/tags"
        params = {
            "page_size": 100,
            "ordering": "-last_updated"
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        tags = data.get("results", [])
        
        if not tags:
            return None, "Keine Tags auf Docker Hub gefunden"
        
        # Suche nach Version-Tags (z.B. v1.0.0, 1.0.0, latest)
        version_tags = []
        for tag in tags:
            tag_name = tag.get("name", "")
            # Ignoriere 'latest' Tag
            if tag_name == "latest":
                continue
            
            # Versuche Version zu extrahieren (z.B. v1.0.0 oder 1.0.0)
            version_match = re.match(r'^v?(\d+\.\d+\.\d+)', tag_name)
            if version_match:
                version_tags.append(version_match.group(1))
        
        if not version_tags:
            # Falls keine Version-Tags gefunden, verwende 'latest' als Fallback
            for tag in tags:
                if tag.get("name") == "latest":
                    return "latest", None
            return None, "Keine Version-Tags gefunden"
        
        # Sortiere Versionen und nehme die neueste
        version_tags.sort(key=lambda v: version.parse(v), reverse=True)
        latest_version = version_tags[0]
        
        return latest_version, None
        
    except requests.exceptions.Timeout:
        return None, "Zeitüberschreitung beim Abrufen der Version"
    except requests.exceptions.RequestException as e:
        return None, f"Fehler beim Abrufen der Version: {str(e)}"
    except Exception as e:
        return None, f"Unerwarteter Fehler: {str(e)}"


def is_update_available(current_version=None):
    """
    Prüft, ob ein Update verfügbar ist.
    
    Args:
        current_version: Aktuelle Version (optional, verwendet CURRENT_VERSION wenn nicht angegeben)
    
    Returns:
        tuple: (is_available, latest_version, error_message)
        - is_available: True wenn Update verfügbar, False sonst
        - latest_version: Neueste Version oder None
        - error_message: Fehlermeldung oder None
    """
    if current_version is None:
        current_version = CURRENT_VERSION
    
    latest_version, error = get_latest_version_from_docker_hub()
    
    if error:
        return False, None, error
    
    if latest_version == "latest":
        # Bei 'latest' können wir nicht vergleichen
        return False, latest_version, None
    
    try:
        # Vergleiche Versionen
        current = version.parse(current_version)
        latest = version.parse(latest_version)
        
        return latest > current, latest_version, None
    except Exception as e:
        return False, latest_version, f"Fehler beim Versionsvergleich: {str(e)}"
