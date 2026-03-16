"""
Einfaches Caching-System für Performance-Optimierung.

Verwendet Flask's g-Objekt für Request-scoped Caching.
Für persistentes Caching kann später Flask-Caching hinzugefügt werden.
"""
from functools import wraps
from flask import g, has_request_context
import time


def get_cache_key(prefix, *args, **kwargs):
    """Generiert einen Cache-Key aus Prefix und Argumenten."""
    key_parts = [str(prefix)]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return "|".join(key_parts)


def cached(timeout=300):
    """
    Decorator für einfaches Request-scoped Caching.
    
    Args:
        timeout: Cache-Timeout in Sekunden (Standard: 5 Minuten)
    
    Performance-Gewinn: Verhindert wiederholte DB-Abfragen innerhalb eines Requests.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not has_request_context():
                # Kein Request-Kontext = kein Caching möglich
                return func(*args, **kwargs)
            
            # Cache-Key generieren
            cache_key = f"cache_{func.__name__}_{get_cache_key('', *args, **kwargs)}"
            
            # Prüfe Cache
            if not hasattr(g, '_cache'):
                g._cache = {}
                g._cache_timestamps = {}
            
            # Prüfe ob im Cache und noch gültig
            if cache_key in g._cache:
                timestamp = g._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < timeout:
                    return g._cache[cache_key]
            
            # Nicht im Cache oder abgelaufen - Funktion ausführen
            result = func(*args, **kwargs)
            
            # In Cache speichern
            g._cache[cache_key] = result
            g._cache_timestamps[cache_key] = time.time()
            
            return result
        return wrapper
    return decorator


def clear_cache():
    """Löscht den Request-scoped Cache (z.B. nach Datenänderungen)."""
    if has_request_context() and hasattr(g, '_cache'):
        g._cache.clear()
        g._cache_timestamps.clear()

