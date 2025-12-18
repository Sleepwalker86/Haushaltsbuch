"""Dashboard-Routen."""
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, flash, url_for, Response
import csv
from io import StringIO

from db import get_connection
from utils.helpers import parse_amount, parse_filter_params, load_filter_data
from services.data_service import (
    fetch_categories, fetch_konten_details, fetch_category_summary,
    fetch_time_series, fetch_buchungen, fetch_einzahlungen_by_iban,
    fetch_total_saldo, fetch_analysis_data, fetch_available_years
)

bp = Blueprint('dashboard', __name__)


@bp.route("/", methods=["GET", "POST"])
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
            return redirect(url_for("dashboard.index"))
        except Exception as exc:
            flash(f"Fehler: {exc}", "error")

    kategorien = fetch_categories()
    konten = []
    try:
        konten = fetch_konten_details()
    except Exception as exc:
        flash(f"Konten konnten nicht geladen werden (Tabelle 'konten' vorhanden?): {exc}", "error")
    return render_template("form.html", kategorien=kategorien, konten=konten)


@bp.route("/dashboard")
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


@bp.route("/dashboard/export")
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


@bp.route("/buchungen")
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


@bp.route("/analysis")
def analysis():
    filters = parse_filter_params()
    year = filters["year"]
    month = filters["month"]
    konto = filters["konto"]
    kategorie_filter = filters["kategorie_filter"]
    compare_year = request.args.get("compare_year", "").strip()
    compare_year = compare_year if compare_year else None

    analysis_data = fetch_analysis_data(
        year,
        month,
        konto=konto or None,
        kategorie_filter=kategorie_filter or None,
        compare_year=compare_year,
    )

    kategorien, konten = load_filter_data()
    available_years = fetch_available_years()

    return render_template(
        "analysis.html",
        year=year,
        selected_months=month,
        konto=konto,
        kategorie_filter=kategorie_filter,
        kategorien=kategorien,
        konten=konten,
        compare_year=compare_year,
        available_years=available_years,
        analysis_data=analysis_data,
    )
