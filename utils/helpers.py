"""Helper-Funktionen für die Anwendung."""
from datetime import date
from flask import request, flash
import os
import json


def parse_amount(amount_str):
    """Konvertiert Betrag-String (mit Komma/Punkt) zu Float."""
    amount_str = amount_str.strip()
    if "," in amount_str:
        amount_str = amount_str.replace(".", "").replace(",", ".")
    elif "." in amount_str:
        parts = amount_str.split(".")
        if len(parts) > 1 and len(parts[-1]) <= 2:
            pass
        else:
            amount_str = amount_str.replace(".", "")
    return abs(float(amount_str))


def parse_filter_params():
    """Extrahiert und validiert Filter-Parameter aus Request."""
    today = date.today()
    default_year = str(today.year)
    default_month = [str(today.month)]
    
    year = request.args.get("year") or default_year
    if year and not year.isdigit():
        year = default_year
    
    month_list = request.args.getlist("month")
    if not month_list:
        month = default_month
    else:
        month = [m for m in month_list if m.isdigit() and 1 <= int(m) <= 12]
        if not month:
            month = default_month
    
    page = int(request.args.get("page", 1))
    if page < 1:
        page = 1
    
    return {
        "year": year,
        "month": month,
        "konto": request.args.get("konto") or "",
        "kategorie_filter": request.args.get("kategorie_filter") or "",
        "kategorie2_filter": request.args.get("kategorie2_filter") or "",
        "page": page,
    }


def load_config():
    """Lädt die Konfiguration aus config.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base_dir, "config.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config):
    """Speichert die Konfiguration in config.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base_dir, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def load_filter_data():
    """Lädt Kategorien und Konten für Filter."""
    from flask import has_request_context, flash
    from services.data_service import fetch_categories, fetch_konten_details
    
    kategorien = fetch_categories()
    konten = []
    try:
        konten = fetch_konten_details()
    except Exception as exc:
        if has_request_context():
            try:
                flash(f"Konten für Filter konnten nicht geladen werden: {exc}", "error")
            except Exception:
                # Falls flash auch fehlschlägt, einfach ignorieren
                pass
    return kategorien, konten
