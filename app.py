from datetime import datetime, date
from flask import Flask, render_template, request, redirect, flash, url_for, Response
import math
import os
import subprocess
import sys
from werkzeug.utils import secure_filename

from db import get_connection
import json

app = Flask(__name__)
app.secret_key = "change-me-please"


@app.context_processor
def inject_config():
    try:
        config = load_config()
        paperless_enabled = config.get("PAPERLESS", {}).get("enabled", False)
    except Exception:
        paperless_enabled = False
    return {"paperless_enabled": paperless_enabled}


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


def load_filter_data():
    """Lädt Kategorien und Konten für Filter."""
    kategorien = fetch_categories()
    konten = []
    try:
        konten = fetch_konten_details()
    except Exception as exc:
        flash(f"Konten für Filter konnten nicht geladen werden: {exc}", "error")
    return kategorien, konten


def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            datum_raw = request.form.get("datum", "").strip()
            betrag_raw = request.form.get("betrag", "").strip()
            beschreibung = request.form.get("beschreibung", "").strip()
            kategorie = request.form.get("kategorie", "").strip()
            kategorie2 = request.form.get("kategorie2", "").strip()
            typ = request.form.get("typ", "Ausgaben").strip()
            konto = request.form.get("konto", "").strip()

            if not datum_raw or not betrag_raw or not kategorie or not konto:
                raise ValueError("Datum, Betrag, Kategorie und Konto sind erforderlich.")

            betrag = parse_amount(betrag_raw)
            datum = datetime.strptime(datum_raw, "%Y-%m-%d").date()

            # Mapping auf soll/haben basierend auf Typ
            if typ == "Ausgaben":
                soll = betrag
                haben = 0
            else:  # Einnahmen
                soll = 0
                haben = betrag

            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO buchungen (datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto, manually_edit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        datum,
                        "Manuell",
                        beschreibung,
                        soll,
                        haben,
                        kategorie,
                        kategorie2,
                        konto,
                        1,
                    ),
                )
                conn.commit()
                cur.close()

            flash("Buchung gespeichert.", "success")
            return redirect(url_for("index"))
        except Exception as exc:
            flash(f"Fehler: {exc}", "error")

    kategorien = fetch_categories()
    konten = []
    try:
        konten = fetch_konten_details()
    except Exception as exc:
        flash(f"Konten konnten nicht geladen werden (Tabelle 'konten' vorhanden?): {exc}", "error")
    return render_template("form.html", kategorien=kategorien, konten=konten)


@app.route("/dashboard")
def dashboard():
    filters = parse_filter_params()
    year = filters["year"]
    month = filters["month"]
    konto = filters["konto"]
    kategorie_filter = filters["kategorie_filter"]
    kategorie2_filter = filters["kategorie2_filter"]
    page = filters["page"]

    cat_summary = fetch_category_summary(year, month)
    time_series = fetch_time_series(year, month)
    buchungen, total_buchungen, total_pages = fetch_buchungen(
        year,
        month,
        page,
        konto=konto or None,
        kategorie_filter=kategorie_filter or None,
        kategorie2_filter=kategorie2_filter or None,
    )
    einzahlungen = fetch_einzahlungen_by_iban(year, month)

    labels_cat = [c["kategorie"] for c in cat_summary]
    values_haben = [c["haben"] for c in cat_summary]
    values_soll = [c["soll"] for c in cat_summary]

    total_haben = sum(values_haben)
    total_soll = sum(values_soll)
    cashflow = total_haben - total_soll

    labels_ts = [t["period"] for t in time_series]
    values_ts = [t["saldo"] for t in time_series]

    labels_iban = [e["iban"] for e in einzahlungen]
    values_iban = [e["betrag"] for e in einzahlungen]

    total_saldo = fetch_total_saldo()
    kategorien, konten = load_filter_data()

    return render_template(
        "dashboard.html",
        year=year,
        selected_months=month,
        labels_cat=labels_cat,
        values_haben=values_haben,
        values_soll=values_soll,
        labels_ts=labels_ts,
        values_ts=values_ts,
        labels_iban=labels_iban,
        values_iban=values_iban,
        buchungen=buchungen,
        current_page=page,
        total_pages=total_pages,
        total_buchungen=total_buchungen,
        kategorien=kategorien,
        konten=konten,
        konto=konto,
        kategorie_filter=kategorie_filter,
        kategorie2_filter=kategorie2_filter,
        total_haben=total_haben,
        total_soll=total_soll,
        total_saldo=total_saldo,
        cashflow=cashflow,
    )


@app.route("/dashboard/export")
def export_buchungen():
    filters = parse_filter_params()
    year = filters["year"]
    month = filters["month"]
    konto = filters["konto"]
    kategorie_filter = filters["kategorie_filter"]
    kategorie2_filter = filters["kategorie2_filter"]

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

    sql = f"""
        SELECT datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto
        FROM buchungen
        {where_sql}
        ORDER BY datum DESC, id DESC
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()

    # CSV erstellen (deutsches Semikolon-Format)
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output, delimiter=";")

    # Kopfzeile
    writer.writerow(
        ["Datum", "Art", "Beschreibung", "Soll", "Haben", "Kategorie", "Unterkategorie", "Konto"]
    )

    for datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto_val in rows:
        if isinstance(datum, (datetime, date)):
            datum_str = datum.strftime("%d.%m.%Y")
        else:
            datum_str = str(datum) if datum is not None else ""
        writer.writerow(
            [
                datum_str,
                art or "",
                beschreibung or "",
                f"{float(soll or 0):.2f}".replace(".", ","),
                f"{float(haben or 0):.2f}".replace(".", ","),
                kategorie or "",
                kategorie2 or "",
                konto_val or "",
            ]
        )

    csv_data = output.getvalue()
    output.close()

    filename = f"buchungen_{year}_{month}.csv"
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/reload-categories", methods=["POST"])
def reload_categories():
    try:
        subprocess.run([sys.executable, "reload_category.py"], check=True)
        flash("Kategorien wurden neu geladen.", "success")
    except subprocess.CalledProcessError as exc:
        flash(f"Fehler beim Neuladen: {exc}", "error")
    return redirect(url_for("dashboard"))

@app.route("/import_data", methods=["POST"])
def import_data():
    try:
        subprocess.run([sys.executable, "import_data.py"], check=True)
        flash("Daten wurden neu eingelesen.", "success")
    except subprocess.CalledProcessError as exc:
        flash(f"Fehler beim lesen der Daten: {exc}", "error")
    return redirect(url_for("dashboard"))


@app.route("/edit/<int:buchung_id>", methods=["GET", "POST"])
def edit_buchung(buchung_id):
    if request.method == "POST":
        try:
            datum_raw = request.form.get("datum", "").strip()
            art = request.form.get("art", "").strip()
            beschreibung = request.form.get("beschreibung", "").strip()
            kategorie = request.form.get("kategorie", "").strip()
            kategorie2 = request.form.get("kategorie2", "").strip()
            typ = request.form.get("typ", "Ausgaben").strip()
            betrag_raw = request.form.get("betrag", "").strip()
            manually_edit_flag = 1 if request.form.get("manually_edit") == "on" else 0

            if not datum_raw or not betrag_raw or not kategorie:
                raise ValueError("Datum, Betrag und Kategorie sind erforderlich.")

            betrag = parse_amount(betrag_raw)
            datum = datetime.strptime(datum_raw, "%Y-%m-%d").date()

            # Mapping auf soll/haben basierend auf Typ
            if typ == "Ausgaben":
                soll = betrag
                haben = 0
            else:  # Einnahmen
                soll = 0
                haben = betrag

            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE buchungen
                    SET datum=%s,
                        art=%s,
                        beschreibung=%s,
                        soll=%s,
                        haben=%s,
                        kategorie=%s,
                        kategorie2=%s,
                        manually_edit=%s
                    WHERE id=%s
                    """,
                    (datum, art, beschreibung, soll, haben, kategorie, kategorie2, manually_edit_flag, buchung_id),
                )
                conn.commit()
                cur.close()

            flash("Buchung aktualisiert.", "success")
            # Prüfen, ob wir von buchungen-Seite kommen
            referer = request.headers.get("Referer", "")
            if "buchungen" in referer:
                return redirect(
                    url_for(
                        "buchungen",
                        year=request.args.get("year"),
                        month=request.args.getlist("month"),
                        page=request.args.get("page", 1),
                        konto=request.args.get("konto", ""),
                        kategorie_filter=request.args.get("kategorie_filter", ""),
                        kategorie2_filter=request.args.get("kategorie2_filter", ""),
                    )
                )
            else:
                return redirect(url_for("dashboard", year=request.args.get("year"), month=request.args.getlist("month"), page=request.args.get("page", 1)))
        except Exception as exc:
            flash(f"Fehler: {exc}", "error")

    # Buchung laden
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto, manually_edit FROM buchungen WHERE id=%s",
            (buchung_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            flash("Buchung nicht gefunden.", "error")
            return redirect(url_for("dashboard"))

        buchung = {
            "id": row[0],
            "datum": row[1],
            "art": row[2] or "",
            "beschreibung": row[3] or "",
            "soll": float(row[4] or 0),
            "haben": float(row[5] or 0),
            "kategorie": row[6] or "",
            "kategorie2": row[7] or "",
            "konto": row[8] or "",
            "manually_edit": int(row[9] or 0),
        }

    kategorien = fetch_categories()
    return render_template("edit_buchung.html", buchung=buchung, kategorien=kategorien)


@app.route("/delete/<int:buchung_id>", methods=["POST"])
def delete_buchung(buchung_id):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM buchungen WHERE id=%s", (buchung_id,))
            conn.commit()
            cur.close()
        flash("Buchung wurde gelöscht.", "success")
    except Exception as exc:
        flash(f"Buchung konnte nicht gelöscht werden: {exc}", "error")

    # Prüfen, ob wir von buchungen-Seite kommen
    referer = request.headers.get("Referer", "")
    if "buchungen" in referer:
        return redirect(
            url_for(
                "buchungen",
                year=request.args.get("year"),
                month=request.args.getlist("month"),
                page=request.args.get("page", 1),
                konto=request.args.get("konto", ""),
                kategorie_filter=request.args.get("kategorie_filter", ""),
                kategorie2_filter=request.args.get("kategorie2_filter", ""),
            )
        )
    else:
        return redirect(
            url_for(
                "dashboard",
                year=request.args.get("year"),
                month=request.args.getlist("month"),
                page=request.args.get("page", 1),
            )
        )

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        form_type = request.form.get("form_type", "konto")

        # ---------------------------------
        # Konto-Formular
        # ---------------------------------
        if form_type == "konto":
            konto_id = request.form.get("konto_id")
            name = request.form.get("name", "").strip()
            beschreibung = request.form.get("beschreibung", "").strip()
            iban = request.form.get("iban", "").strip()

            if not name:
                flash("Name des Kontos ist erforderlich.", "error")
            else:
                try:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        if konto_id:
                            cur.execute(
                                """
                                UPDATE konten
                                SET name=%s, beschreibung=%s, iban=%s
                                WHERE id=%s
                                """,
                                (name, beschreibung, iban, konto_id),
                            )
                            flash("Konto wurde aktualisiert.", "success")
                        else:
                            cur.execute(
                                """
                                INSERT INTO konten (name, beschreibung, iban)
                                VALUES (%s, %s, %s)
                                """,
                                (name, beschreibung, iban),
                            )
                            flash("Konto wurde angelegt.", "success")
                        conn.commit()
                        cur.close()
                except Exception as exc:
                    flash(f"Konto konnte nicht angelegt werden: {exc}", "error")

            return redirect(url_for("settings", tab="konten"))

        # ---------------------------------
        # Konto löschen
        # ---------------------------------
        elif form_type == "konto_delete":
            konto_id = request.form.get("konto_id")
            if not konto_id:
                flash("Konto konnte nicht gelöscht werden: ID fehlt.", "error")
            else:
                try:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("DELETE FROM konten WHERE id=%s", (konto_id,))
                        conn.commit()
                        cur.close()
                    flash("Konto wurde gelöscht.", "success")
                except Exception as exc:
                    flash(f"Konto konnte nicht gelöscht werden: {exc}", "error")

            return redirect(url_for("settings", tab="konten"))

        # ---------------------------------
        # Keyword-Category-Formular
        # ---------------------------------
        elif form_type == "keyword":
            mapping_id = request.form.get("mapping_id")
            keyword = request.form.get("keyword", "").strip()
            category_name = request.form.get("category_name", "").strip()

            if not keyword or not category_name:
                flash("Kategorie und Schlüsselwort sind erforderlich.", "error")
            else:
                try:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        if mapping_id:
                            # Update bestehender Zuordnung
                            cur.execute(
                                """
                                UPDATE keyword_category
                                SET schluesselwort=%s, kategorie=%s
                                WHERE id=%s
                                """,
                                (keyword, category_name, mapping_id),
                            )
                            flash("Zuordnung wurde aktualisiert.", "success")
                        else:
                            # Neue Zuordnung anlegen
                            cur.execute(
                                """
                                INSERT INTO keyword_category (schluesselwort, kategorie)
                                VALUES (%s, %s)
                                """,
                                (keyword, category_name),
                            )
                            flash("Zuordnung wurde gespeichert.", "success")
                        conn.commit()
                        cur.close()
                except Exception as exc:
                    flash(f"Zuordnung konnte nicht gespeichert werden: {exc}", "error")

            return redirect(url_for("settings", tab="keywords"))

        # ---------------------------------
        # Kategorie-Stammdaten (Tabelle category)
        # ---------------------------------
        elif form_type == "category_master":
            category_name = request.form.get("category_name", "").strip()
            if not category_name:
                flash("Name der Kategorie ist erforderlich.", "error")
            else:
                try:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT IGNORE INTO category (name)
                            VALUES (%s)
                            """,
                            (category_name,),
                        )
                        conn.commit()
                        cur.close()
                    flash("Kategorie wurde gespeichert.", "success")
                except Exception as exc:
                    flash(f"Kategorie konnte nicht gespeichert werden: {exc}", "error")

            return redirect(url_for("settings", tab="keywords"))

        # ---------------------------------
        # Keyword-Category-Löschen
        # ---------------------------------
        elif form_type == "keyword_delete":
            mapping_id = request.form.get("mapping_id")
            if not mapping_id:
                flash("Zuordnung konnte nicht gelöscht werden: ID fehlt.", "error")
            else:
                try:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "DELETE FROM keyword_category WHERE id=%s",
                            (mapping_id,),
                        )
                        conn.commit()
                        cur.close()
                    flash("Zuordnung wurde gelöscht.", "success")
                except Exception as exc:
                    flash(f"Zuordnung konnte nicht gelöscht werden: {exc}", "error")

            return redirect(url_for("settings", tab="keywords"))

        # ---------------------------------
        # Kategorie-Stammdaten-Löschen
        # ---------------------------------
        elif form_type == "category_delete":
            category_id = request.form.get("category_id")
            if not category_id:
                flash("Kategorie konnte nicht gelöscht werden: ID fehlt.", "error")
            else:
                try:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        # Zuerst alle zugehörigen Zuordnungen in keyword_category löschen
                        cur.execute(
                            """
                            DELETE FROM keyword_category
                            WHERE kategorie = (SELECT name FROM category WHERE id=%s)
                            """,
                            (category_id,),
                        )
                        # Dann die Kategorie selbst löschen
                        cur.execute(
                            "DELETE FROM category WHERE id=%s",
                            (category_id,),
                        )
                        conn.commit()
                        cur.close()
                    flash("Kategorie wurde gelöscht.", "success")
                except Exception as exc:
                    flash(f"Kategorie konnte nicht gelöscht werden: {exc}", "error")

            return redirect(url_for("settings", tab="keywords"))

        # ---------------------------------
        # Paperless-Einstellungen
        # ---------------------------------
        elif form_type == "paperless":
            paperless_enabled = request.form.get("paperless_enabled") == "on"
            paperless_ip = request.form.get("paperless_ip", "").strip()
            paperless_token = request.form.get("paperless_token", "").strip()
            document_type_id = request.form.get("document_type_id", "").strip()
            try:
                config = load_config()
                if "PAPERLESS" not in config:
                    config["PAPERLESS"] = {}
                config["PAPERLESS"]["enabled"] = paperless_enabled
                config["PAPERLESS"]["ip"] = paperless_ip
                config["PAPERLESS"]["token"] = paperless_token
                config["PAPERLESS"]["document_type_id"] = document_type_id
                save_config(config)
                flash("Paperless-Einstellungen wurden gespeichert.", "success")
            except Exception as exc:
                flash(f"Paperless-Einstellungen konnten nicht gespeichert werden: {exc}", "error")

            return redirect(url_for("settings", tab="paperless"))

    konten = []
    try:
        konten = fetch_konten_details()
    except Exception as exc:
        flash(f"Konten konnten nicht geladen werden (Tabelle vorhanden?): {exc}", "error")

    # Optional: Konto zum Bearbeiten vorselektieren (Future: eigenes Edit-Formular)
    edit_id = request.args.get("edit_id")
    edit_konto = None
    if edit_id:
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, name, beschreibung, iban FROM konten WHERE id=%s",
                    (edit_id,),
                )
                row = cur.fetchone()
                cur.close()
            if row:
                edit_konto = {
                    "id": row[0],
                    "name": row[1] or "",
                    "beschreibung": row[2] or "",
                    "iban": row[3] or "",
                }
        except Exception:
            pass

    # Daten für Keyword-Category-Tab
    categories_master = []
    keyword_mappings = []
    edit_mapping = None
    try:
        categories_master = fetch_category_master()
        keyword_mappings = fetch_keyword_mappings()

        # Optional einzelne Zuordnung zum Bearbeiten laden
        mapping_id = request.args.get("mapping_id")
        if mapping_id:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, schluesselwort, kategorie FROM keyword_category WHERE id=%s",
                    (mapping_id,),
                )
                row = cur.fetchone()
                cur.close()
            if row:
                edit_mapping = {
                    "id": row[0],
                    "schluesselwort": row[1] or "",
                    "kategorie": row[2] or "",
                }
    except Exception:
        # Nur still schlucken, Anzeige wird dann leer
        pass

    # Paperless-Einstellungen laden
    paperless_config = {"enabled": False, "ip": "", "token": "", "document_type_id": ""}
    try:
        config = load_config()
        if "PAPERLESS" in config:
            paperless_config = {
                "enabled": config["PAPERLESS"].get("enabled", False),
                "ip": config["PAPERLESS"].get("ip", ""),
                "token": config["PAPERLESS"].get("token", ""),
                "document_type_id": config["PAPERLESS"].get("document_type_id", ""),
            }
    except Exception:
        pass

    active_tab = request.args.get("tab")
    if active_tab not in ("konten", "keywords", "paperless"):
        active_tab = "konten"

    return render_template(
        "settings.html",
        konten=konten,
        edit_konto=edit_konto,
        categories_master=categories_master,
        keyword_mappings=keyword_mappings,
        edit_mapping=edit_mapping,
        paperless_config=paperless_config,
        active_tab=active_tab,
    )


@app.route("/upload", methods=["GET"])
def upload():
    """Separate Seite für CSV-Upload und -Verarbeitung."""
    return render_template("upload_data.html")


@app.route("/paperless", methods=["GET", "POST"])
def paperless():
    if request.method == "POST":
        file = request.files.get("image_file")
        if not file or file.filename == "":
            flash("Bitte ein Bild auswählen oder aufnehmen.", "error")
            return redirect(url_for("paperless"))

        # Erlaubte Bildformate
        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif"}
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            flash("Nur Bilddateien (PDF, JPG, PNG, HEIC) sind erlaubt.", "error")
            return redirect(url_for("paperless"))

        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_dir = os.path.join(base_dir, "image")
        os.makedirs(image_dir, exist_ok=True)

        # Eindeutigen Dateinamen erstellen mit Timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = os.path.splitext(filename)[0]
        new_filename = f"{timestamp}_{safe_name}{file_ext}"
        target_path = os.path.join(image_dir, new_filename)

        try:
            file.save(target_path)
            flash(f"Bild '{new_filename}' wurde erfolgreich gespeichert.", "success")
        except Exception as exc:
            flash(f"Bild konnte nicht gespeichert werden: {exc}", "error")

        return redirect(url_for("paperless"))

    # GET: Seite anzeigen
    return render_template("paperless.html", title="Paperless")


@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    file = request.files.get("csv_file")
    if not file or file.filename == "":
        flash("Bitte eine CSV-Datei auswählen.", "error")
        return redirect(url_for("upload"))

    filename = os.path.basename(file.filename)
    if not filename.lower().endswith(".csv"):
        flash("Nur CSV-Dateien sind erlaubt.", "error")
        return redirect(url_for("upload"))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    import_dir = os.path.join(base_dir, "import")
    os.makedirs(import_dir, exist_ok=True)

    target_path = os.path.join(import_dir, filename)
    try:
        file.save(target_path)
        flash(f"Datei '{filename}' wurde nach 'import' hochgeladen.", "success")
    except Exception as exc:
        flash(f"CSV konnte nicht hochgeladen werden: {exc}", "error")

    return redirect(url_for("upload"))


def fetch_analysis_data(year, month, konto=None, kategorie_filter=None):
    """
    Holt Daten für Analyse-Seite: aktuelles Jahr und Vorjahr.
    Gibt zurück: {
        'current': {einnahmen, ausgaben, cashflow, kategorien, ...},
        'previous': {einnahmen, ausgaben, cashflow, kategorien, ...}
    }
    """
    previous_year = str(int(year) - 1)
    
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
    
    # Vorjahr (gleiche Monate)
    where_previous = []
    params_previous = []
    where_previous.append("YEAR(datum) = %s")
    params_previous.append(previous_year)
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
    where_sql_previous = f"WHERE {' AND '.join(where_previous)}"
    
    # Gesamtwerte aktuelles Jahr
    sql_current = f"""
        SELECT 
            SUM(haben) AS total_haben,
            SUM(soll) AS total_soll,
            SUM(haben - soll) AS cashflow
        FROM buchungen
        {where_sql_current}
    """
    
    # Gesamtwerte Vorjahr
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
    
    # Kategorien Vorjahr
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
    
    # Monatliche Zeitreihe Vorjahr
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
        
        # Vorjahr
        cur.execute(sql_previous, params_previous)
        row_previous = cur.fetchone()
        previous_total = {
            "haben": float(row_previous[0] or 0),
            "soll": float(row_previous[1] or 0),
            "cashflow": float(row_previous[2] or 0),
        }
        
        # Kategorien aktuelles Jahr
        cur.execute(sql_cat_current, params_current)
        rows_cat_current = cur.fetchall()
        current_categories = [
            {"kategorie": r[0] or "", "haben": float(r[1] or 0), "soll": float(r[2] or 0)}
            for r in rows_cat_current
        ]
        
        # Kategorien Vorjahr
        cur.execute(sql_cat_previous, params_previous)
        rows_cat_previous = cur.fetchall()
        previous_categories = [
            {"kategorie": r[0] or "", "haben": float(r[1] or 0), "soll": float(r[2] or 0)}
            for r in rows_cat_previous
        ]
        
        # Zeitreihen
        cur.execute(sql_ts_current, params_current)
        rows_ts_current = cur.fetchall()
        current_timeseries = [
            {"month": int(r[0]), "haben": float(r[1] or 0), "soll": float(r[2] or 0), "cashflow": float(r[3] or 0)}
            for r in rows_ts_current
        ]
        
        cur.execute(sql_ts_previous, params_previous)
        rows_ts_previous = cur.fetchall()
        previous_timeseries = [
            {"month": int(r[0]), "haben": float(r[1] or 0), "soll": float(r[2] or 0), "cashflow": float(r[3] or 0)}
            for r in rows_ts_previous
        ]
        
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


@app.route("/buchungen")
def buchungen():
    filters = parse_filter_params()
    year = filters["year"]
    month = filters["month"]
    konto = filters["konto"]
    kategorie_filter = filters["kategorie_filter"]
    kategorie2_filter = filters["kategorie2_filter"]
    page = filters["page"]

    buchungen_list, total_buchungen, total_pages = fetch_buchungen(
        year,
        month,
        page,
        per_page=100,
        konto=konto or None,
        kategorie_filter=kategorie_filter or None,
        kategorie2_filter=kategorie2_filter or None,
    )

    kategorien, konten = load_filter_data()

    return render_template(
        "buchungen.html",
        year=year,
        selected_months=month,
        buchungen=buchungen_list,
        current_page=page,
        total_pages=total_pages,
        total_buchungen=total_buchungen,
        kategorien=kategorien,
        konten=konten,
        konto=konto,
        kategorie_filter=kategorie_filter,
        kategorie2_filter=kategorie2_filter,
    )


@app.route("/analysis")
def analysis():
    filters = parse_filter_params()
    year = filters["year"]
    month = filters["month"]
    konto = filters["konto"]
    kategorie_filter = filters["kategorie_filter"]
    compare_yoy = request.args.get("compare_yoy", "1") == "1"

    analysis_data = fetch_analysis_data(
        year,
        month,
        konto=konto or None,
        kategorie_filter=kategorie_filter or None,
    )

    kategorien, konten = load_filter_data()

    return render_template(
        "analysis.html",
        year=year,
        selected_months=month,
        konto=konto,
        kategorie_filter=kategorie_filter,
        kategorien=kategorien,
        konten=konten,
        compare_yoy=compare_yoy,
        analysis_data=analysis_data,
    )


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(debug=debug, host="0.0.0.0", port=5001)

