from datetime import datetime, date
from flask import Flask, render_template, request, redirect, flash, url_for
import math
import os
import subprocess
import sys

from db import get_connection

app = Flask(__name__)
app.secret_key = "change-me-please"  # für Flash-Messages


def fetch_categories():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT kategorie FROM kategorien ORDER BY kategorie")
        rows = cur.fetchall()
        cur.close()
        kategorien = [row[0] for row in rows]
        # "Sonstiges" hinzufügen, falls nicht vorhanden
        if "Sonstiges" not in kategorien:
            kategorien.append("Sonstiges")
        return kategorien


def fetch_category_summary(year=None, month=None):
    where = []
    params = []
    if year:
        where.append("YEAR(datum) = %s")
        params.append(year)
    if month:
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


def fetch_buchungen(year=None, month=None, page=1, per_page=30, konto=None, kategorie2_filter=None):
    where = []
    params = []
    if year:
        where.append("YEAR(datum) = %s")
        params.append(year)
    if month:
        where.append("MONTH(datum) = %s")
        params.append(month)
    if konto:
        where.append("konto = %s")
        params.append(konto)
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

            # Betrag parsen (unterstützt Komma und Punkt als Dezimaltrenner)
            betrag_str = betrag_raw.strip()
            # Wenn Komma vorhanden, ist es Dezimaltrenner (deutsches Format)
            if "," in betrag_str:
                betrag_str = betrag_str.replace(".", "").replace(",", ".")
            # Wenn nur Punkt vorhanden, prüfe ob Dezimaltrenner (max 2 Nachkommastellen)
            elif "." in betrag_str:
                parts = betrag_str.split(".")
                # Wenn nach dem letzten Punkt nur 1-2 Ziffern, ist es Dezimaltrenner
                if len(parts) > 1 and len(parts[-1]) <= 2:
                    # Punkt ist Dezimaltrenner, behalte ihn
                    betrag_str = betrag_str
                else:
                    # Punkt ist Tausender-Trenner, entferne ihn
                    betrag_str = betrag_str.replace(".", "")
            betrag = abs(float(betrag_str))
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
    # Standard-Filter auf aktuelles Jahr/Monat
    today = date.today()
    default_year = str(today.year)
    default_month = str(today.month)
    
    year = request.args.get("year") or default_year
    month = request.args.get("month") or default_month
    konto = request.args.get("konto") or ""
    kategorie2_filter = request.args.get("kategorie2_filter") or ""
    page = int(request.args.get("page", 1))
    
    if year and not year.isdigit():
        year = default_year
    if month and not month.isdigit():
        month = default_month
    if page < 1:
        page = 1

    cat_summary = fetch_category_summary(year, month)
    time_series = fetch_time_series(year, month)
    buchungen, total_buchungen, total_pages = fetch_buchungen(
        year, month, page, konto=konto or None, kategorie2_filter=kategorie2_filter or None
    )
    einzahlungen = fetch_einzahlungen_by_iban(year, month)

    labels_cat = [c["kategorie"] for c in cat_summary]
    values_haben = [c["haben"] for c in cat_summary]
    values_soll = [c["soll"] for c in cat_summary]

    labels_ts = [t["period"] for t in time_series]
    values_ts = [t["saldo"] for t in time_series]

    labels_iban = [e["iban"] for e in einzahlungen]
    values_iban = [e["betrag"] for e in einzahlungen]

    kategorien = fetch_categories()
    konten = []
    try:
        konten = fetch_konten_details()
    except Exception as exc:
        flash(f"Konten für Filter konnten nicht geladen werden (Tabelle 'konten' vorhanden?): {exc}", "error")

    return render_template(
        "dashboard.html",
        year=year or "",
        month=month or "",
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
        kategorie2_filter=kategorie2_filter,
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

            if not datum_raw or not betrag_raw or not kategorie:
                raise ValueError("Datum, Betrag und Kategorie sind erforderlich.")

            # Betrag parsen (unterstützt Komma und Punkt als Dezimaltrenner)
            betrag_str = betrag_raw.strip()
            # Wenn Komma vorhanden, ist es Dezimaltrenner (deutsches Format)
            if "," in betrag_str:
                betrag_str = betrag_str.replace(".", "").replace(",", ".")
            # Wenn nur Punkt vorhanden, prüfe ob Dezimaltrenner (max 2 Nachkommastellen)
            elif "." in betrag_str:
                parts = betrag_str.split(".")
                # Wenn nach dem letzten Punkt nur 1-2 Ziffern, ist es Dezimaltrenner
                if len(parts) > 1 and len(parts[-1]) <= 2:
                    # Punkt ist Dezimaltrenner, behalte ihn
                    betrag_str = betrag_str
                else:
                    # Punkt ist Tausender-Trenner, entferne ihn
                    betrag_str = betrag_str.replace(".", "")
            betrag = abs(float(betrag_str))
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
                        manually_edit=1
                    WHERE id=%s
                    """,
                    (datum, art, beschreibung, soll, haben, kategorie, kategorie2, buchung_id),
                )
                conn.commit()
                cur.close()

            flash("Buchung aktualisiert.", "success")
            return redirect(url_for("dashboard", year=request.args.get("year"), month=request.args.get("month"), page=request.args.get("page", 1)))
        except Exception as exc:
            flash(f"Fehler: {exc}", "error")

    # Buchung laden
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto FROM buchungen WHERE id=%s",
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

    return redirect(
        url_for(
            "dashboard",
            year=request.args.get("year"),
            month=request.args.get("month"),
            page=request.args.get("page", 1),
        )
    )

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
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

    active_tab = request.args.get("tab")
    if active_tab not in ("upload", "konten"):
        active_tab = "konten" if edit_konto else "upload"

    return render_template("settings.html", konten=konten, edit_konto=edit_konto, active_tab=active_tab)


@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    file = request.files.get("csv_file")
    if not file or file.filename == "":
        flash("Bitte eine CSV-Datei auswählen.", "error")
        return redirect(url_for("settings"))

    filename = os.path.basename(file.filename)
    if not filename.lower().endswith(".csv"):
        flash("Nur CSV-Dateien sind erlaubt.", "error")
        return redirect(url_for("settings"))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    import_dir = os.path.join(base_dir, "import")
    os.makedirs(import_dir, exist_ok=True)

    target_path = os.path.join(import_dir, filename)
    try:
        file.save(target_path)
        flash(f"Datei '{filename}' wurde nach 'import' hochgeladen.", "success")
    except Exception as exc:
        flash(f"CSV konnte nicht hochgeladen werden: {exc}", "error")

    return redirect(url_for("settings"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)

