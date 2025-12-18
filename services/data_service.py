"""Datenbank-Service-Funktionen für die Anwendung."""
import math
from db import get_connection


def fetch_available_years():
    """Holt alle verfügbaren Jahre aus der Datenbank."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT YEAR(datum) FROM buchungen ORDER BY YEAR(datum) DESC")
        years = [str(row[0]) for row in cur.fetchall()]
        cur.close()
        return years


def fetch_categories():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM category ORDER BY name")
        rows = cur.fetchall()
        cur.close()
        kategorien = [row[0] for row in rows]
        if "Sonstiges" not in kategorien:
            kategorien.append("Sonstiges")
        return kategorien


def fetch_category_master():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM category ORDER BY name")
        rows = cur.fetchall()
        cur.close()
        return [{"id": r[0], "name": r[1]} for r in rows]


def fetch_keyword_mappings():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, schluesselwort, kategorie FROM keyword_category ORDER BY kategorie, schluesselwort"
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {"id": r[0], "schluesselwort": r[1], "kategorie": r[2]}
            for r in rows
        ]


def fetch_category_summary(year=None, month=None):
    where = []
    params = []
    if year:
        where.append("YEAR(datum) = %s")
        params.append(year)
    if month:
        if isinstance(month, list):
            placeholders = ",".join(["%s"] * len(month))
            where.append(f"MONTH(datum) IN ({placeholders})")
            params.extend(month)
        else:
            where.append("MONTH(datum) = %s")
            params.append(month)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"""
        SELECT kategorie,
               SUM(haben) AS haben_sum,
               SUM(soll) AS soll_sum
        FROM buchungen
        {where_sql}
        GROUP BY kategorie
        ORDER BY kategorie
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [
            {"kategorie": r[0], "haben": float(r[1] or 0), "soll": float(r[2] or 0)}
            for r in rows
        ]


def fetch_time_series(year=None, month=None):
    where = []
    params = []
    if year:
        where.append("YEAR(datum) = %s")
        params.append(year)
    if month:
        if isinstance(month, list):
            placeholders = ",".join(["%s"] * len(month))
            where.append(f"MONTH(datum) IN ({placeholders})")
            params.extend(month)
        else:
            where.append("MONTH(datum) = %s")
            params.append(month)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"""
        SELECT DATE_FORMAT(datum, '%%Y-%%m-01') AS period,
               SUM(haben - soll) AS saldo
        FROM buchungen
        {where_sql}
        GROUP BY period
        ORDER BY period
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [{"period": r[0], "saldo": float(r[1] or 0)} for r in rows]


def fetch_einzahlungen_by_iban(year=None, month=None):
    where = ["haben > 0", "gegen_iban IS NOT NULL", "gegen_iban != ''"]
    params = []
    if year:
        where.append("YEAR(datum) = %s")
        params.append(year)
    if month:
        if isinstance(month, list):
            placeholders = ",".join(["%s"] * len(month))
            where.append(f"MONTH(datum) IN ({placeholders})")
            params.extend(month)
        else:
            where.append("MONTH(datum) = %s")
            params.append(month)
    where_sql = f"WHERE {' AND '.join(where)}"
    sql = f"""
        SELECT gegen_iban,
               SUM(haben) AS total_haben
        FROM buchungen
        {where_sql}
        GROUP BY gegen_iban
        ORDER BY total_haben DESC
        LIMIT 20
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [
            {"iban": r[0] or "Unbekannt", "betrag": float(r[1] or 0)}
            for r in rows
        ]


def fetch_konten():
    """Liefert alle unterschiedlichen Konten für Filter-Dropdown."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT konto FROM buchungen WHERE konto IS NOT NULL AND konto != '' ORDER BY konto"
        )
        rows = cur.fetchall()
        cur.close()
        return [r[0] for r in rows]


def fetch_konten_details():
    """Liefert Konten aus der Konten-Tabelle (für Einstellungen)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, beschreibung, iban FROM konten ORDER BY name"
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "name": r[1] or "",
                "beschreibung": r[2] or "",
                "iban": r[3] or "",
            }
            for r in rows
        ]


def fetch_buchungen(year=None, month=None, page=1, per_page=30, konto=None, kategorie2_filter=None, kategorie_filter=None):
    where = []
    params = []
    if year:
        where.append("YEAR(datum) = %s")
        params.append(year)
    if month:
        if isinstance(month, list):
            placeholders = ",".join(["%s"] * len(month))
            where.append(f"MONTH(datum) IN ({placeholders})")
            params.extend(month)
        else:
            where.append("MONTH(datum) = %s")
            params.append(month)
    if konto:
        where.append("konto = %s")
        params.append(konto)
    if kategorie_filter:
        where.append("kategorie = %s")
        params.append(kategorie_filter)
    if kategorie2_filter:
        where.append("kategorie2 LIKE %s")
        params.append(f"%{kategorie2_filter}%")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    
    # Gesamtanzahl
    count_sql = f"SELECT COUNT(*) FROM buchungen {where_sql}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]
        cur.close()
    
    # Buchungen mit Pagination
    offset = (page - 1) * per_page
    sql = f"""
        SELECT id, datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto
        FROM buchungen
        {where_sql}
        ORDER BY datum DESC, id DESC
        LIMIT %s OFFSET %s
    """
    params_with_pagination = params + [per_page, offset]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params_with_pagination)
        rows = cur.fetchall()
        cur.close()
        buchungen = [
            {
                "id": r[0],
                "datum": r[1],
                "art": r[2] or "",
                "beschreibung": r[3] or "",
                "soll": float(r[4] or 0),
                "haben": float(r[5] or 0),
                "kategorie": r[6] or "",
                "kategorie2": r[7] or "",
                "konto": r[8] or "",
            }
            for r in rows
        ]

    
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    return buchungen, total, total_pages


def fetch_total_saldo():
    """Gibt den aktuellen Gesamtsaldo über alle Buchungen zurück (Haben - Soll)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(IFNULL(haben,0) - IFNULL(soll,0)), 0) AS saldo FROM buchungen"
        )
        row = cur.fetchone()
        cur.close()
        return float(row[0] or 0)


def fetch_analysis_data(year, month, konto=None, kategorie_filter=None, compare_year=None):
    """
    Holt Daten für Analyse-Seite: aktuelles Jahr und Vergleichsjahr.
    Gibt zurück: {
        'current': {einnahmen, ausgaben, cashflow, kategorien, ...},
        'previous': {einnahmen, ausgaben, cashflow, kategorien, ...}
    }
    """
    # Wenn kein Vergleichsjahr angegeben, wird keines verwendet
    if not compare_year:
        compare_year = None
    else:
        compare_year = str(compare_year)
    
    # Aktuelles Jahr
    where_current = []
    params_current = []
    if year:
        where_current.append("YEAR(datum) = %s")
        params_current.append(year)
    if month:
        if isinstance(month, list):
            placeholders = ",".join(["%s"] * len(month))
            where_current.append(f"MONTH(datum) IN ({placeholders})")
            params_current.extend(month)
        else:
            where_current.append("MONTH(datum) = %s")
            params_current.append(month)
    if konto:
        where_current.append("konto = %s")
        params_current.append(konto)
    if kategorie_filter:
        where_current.append("kategorie = %s")
        params_current.append(kategorie_filter)
    where_sql_current = f"WHERE {' AND '.join(where_current)}" if where_current else ""
    
    # Vergleichsjahr (gleiche Monate) - nur wenn angegeben
    where_previous = []
    params_previous = []
    if compare_year:
        where_previous.append("YEAR(datum) = %s")
        params_previous.append(compare_year)
    if month:
        if isinstance(month, list):
            placeholders = ",".join(["%s"] * len(month))
            where_previous.append(f"MONTH(datum) IN ({placeholders})")
            params_previous.extend(month)
        else:
            where_previous.append("MONTH(datum) = %s")
            params_previous.append(month)
    if konto:
        where_previous.append("konto = %s")
        params_previous.append(konto)
    if kategorie_filter:
        where_previous.append("kategorie = %s")
        params_previous.append(kategorie_filter)
    where_sql_previous = f"WHERE {' AND '.join(where_previous)}" if where_previous else ""
    
    # Gesamtwerte aktuelles Jahr
    sql_current = f"""
        SELECT 
            SUM(haben) AS total_haben,
            SUM(soll) AS total_soll,
            SUM(haben - soll) AS cashflow
        FROM buchungen
        {where_sql_current}
    """
    
    # Gesamtwerte Vergleichsjahr
    sql_previous = f"""
        SELECT 
            SUM(haben) AS total_haben,
            SUM(soll) AS total_soll,
            SUM(haben - soll) AS cashflow
        FROM buchungen
        {where_sql_previous}
    """
    
    # Kategorien aktuelles Jahr
    sql_cat_current = f"""
        SELECT 
            kategorie,
            SUM(haben) AS haben_sum,
            SUM(soll) AS soll_sum
        FROM buchungen
        {where_sql_current}
        GROUP BY kategorie
        ORDER BY kategorie
    """
    
    # Kategorien Vergleichsjahr
    sql_cat_previous = f"""
        SELECT 
            kategorie,
            SUM(haben) AS haben_sum,
            SUM(soll) AS soll_sum
        FROM buchungen
        {where_sql_previous}
        GROUP BY kategorie
        ORDER BY kategorie
    """
    
    # Monatliche Zeitreihe aktuelles Jahr
    sql_ts_current = f"""
        SELECT 
            MONTH(datum) AS month_num,
            SUM(haben) AS haben_sum,
            SUM(soll) AS soll_sum,
            SUM(haben - soll) AS cashflow
        FROM buchungen
        {where_sql_current}
        GROUP BY MONTH(datum)
        ORDER BY MONTH(datum)
    """
    
    # Monatliche Zeitreihe Vergleichsjahr
    sql_ts_previous = f"""
        SELECT 
            MONTH(datum) AS month_num,
            SUM(haben) AS haben_sum,
            SUM(soll) AS soll_sum,
            SUM(haben - soll) AS cashflow
        FROM buchungen
        {where_sql_previous}
        GROUP BY MONTH(datum)
        ORDER BY MONTH(datum)
    """
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Aktuelles Jahr
        cur.execute(sql_current, params_current)
        row_current = cur.fetchone()
        current_total = {
            "haben": float(row_current[0] or 0),
            "soll": float(row_current[1] or 0),
            "cashflow": float(row_current[2] or 0),
        }
        
        # Vergleichsjahr (nur wenn angegeben)
        if compare_year:
            cur.execute(sql_previous, params_previous)
            row_previous = cur.fetchone()
            previous_total = {
                "haben": float(row_previous[0] or 0),
                "soll": float(row_previous[1] or 0),
                "cashflow": float(row_previous[2] or 0),
            }
        else:
            previous_total = {
                "haben": 0.0,
                "soll": 0.0,
                "cashflow": 0.0,
            }
        
        # Kategorien aktuelles Jahr
        cur.execute(sql_cat_current, params_current)
        rows_cat_current = cur.fetchall()
        current_categories = [
            {"kategorie": r[0] or "", "haben": float(r[1] or 0), "soll": float(r[2] or 0)}
            for r in rows_cat_current
        ]
        
        # Kategorien Vergleichsjahr (nur wenn angegeben)
        if compare_year:
            cur.execute(sql_cat_previous, params_previous)
            rows_cat_previous = cur.fetchall()
            previous_categories = [
                {"kategorie": r[0] or "", "haben": float(r[1] or 0), "soll": float(r[2] or 0)}
                for r in rows_cat_previous
            ]
        else:
            previous_categories = []
        
        # Zeitreihen
        cur.execute(sql_ts_current, params_current)
        rows_ts_current = cur.fetchall()
        current_timeseries = [
            {"month": int(r[0]), "haben": float(r[1] or 0), "soll": float(r[2] or 0), "cashflow": float(r[3] or 0)}
            for r in rows_ts_current
        ]
        
        if compare_year:
            cur.execute(sql_ts_previous, params_previous)
            rows_ts_previous = cur.fetchall()
            previous_timeseries = [
                {"month": int(r[0]), "haben": float(r[1] or 0), "soll": float(r[2] or 0), "cashflow": float(r[3] or 0)}
                for r in rows_ts_previous
            ]
        else:
            previous_timeseries = []
        
        cur.close()
    
    # Sparquote berechnen
    current_total["sparquote"] = (current_total["cashflow"] / current_total["haben"] * 100) if current_total["haben"] > 0 else 0
    previous_total["sparquote"] = (previous_total["cashflow"] / previous_total["haben"] * 100) if previous_total["haben"] > 0 else 0
    
    # Deltas berechnen
    deltas = {
        "haben": current_total["haben"] - previous_total["haben"],
        "soll": current_total["soll"] - previous_total["soll"],
        "cashflow": current_total["cashflow"] - previous_total["cashflow"],
        "sparquote": current_total["sparquote"] - previous_total["sparquote"],
    }
    
    # Prozentuale Änderungen
    deltas_pct = {
        "haben": (deltas["haben"] / previous_total["haben"] * 100) if previous_total["haben"] > 0 else 0,
        "soll": (deltas["soll"] / previous_total["soll"] * 100) if previous_total["soll"] > 0 else 0,
        "cashflow": (deltas["cashflow"] / abs(previous_total["cashflow"]) * 100) if previous_total["cashflow"] != 0 else 0,
        "sparquote": deltas["sparquote"],
    }
    
    return {
        "current": {
            **current_total,
            "categories": current_categories,
            "timeseries": current_timeseries,
        },
        "previous": {
            **previous_total,
            "categories": previous_categories,
            "timeseries": previous_timeseries,
        },
        "deltas": deltas,
        "deltas_pct": deltas_pct,
    }
