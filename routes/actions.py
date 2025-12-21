"""Aktions-Routen (Edit, Delete, Import, etc.)."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash, url_for
import subprocess
import sys
import os

from db import get_connection
from utils.helpers import parse_amount
from services.data_service import fetch_categories

bp = Blueprint('actions', __name__)


@bp.route("/reload-categories", methods=["POST"])
def reload_categories():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run([sys.executable, "reload_category.py"], check=True, cwd=base_dir)
        flash("Kategorien wurden neu geladen.", "success")
    except subprocess.CalledProcessError as exc:
        flash(f"Fehler beim Neuladen: {exc}", "error")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/import_data", methods=["POST"])
def import_data():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run([sys.executable, "import_data.py"], check=True, cwd=base_dir)
        flash("Daten wurden neu eingelesen.", "success")
    except subprocess.CalledProcessError as exc:
        flash(f"Fehler beim lesen der Daten: {exc}", "error")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/edit/<int:buchung_id>", methods=["GET", "POST"])
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
            # Prüfen, ob wir von buchungen-Seite kommen (anhand des return_to Parameters)
            # Beim POST kommen die Parameter aus request.form (versteckte Felder), 
            # beim GET aus request.args
            params_source = request.form if request.method == "POST" else request.args
            return_to = params_source.get("return_to", "")
            
            if return_to == "buchungen":
                return redirect(
                    url_for(
                        "dashboard.buchungen",
                        year=params_source.get("year"),
                        month=params_source.getlist("month"),
                        page=params_source.get("page", 1),
                        konto=params_source.get("konto", ""),
                        kategorie_filter=params_source.get("kategorie_filter", ""),
                        kategorie2_filter=params_source.get("kategorie2_filter", ""),
                        beschreibung_filter=params_source.get("beschreibung_filter", ""),
                    )
                )
            else:
                return redirect(url_for("dashboard.dashboard", year=params_source.get("year"), month=params_source.getlist("month"), page=params_source.get("page", 1)))
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
            return redirect(url_for("dashboard.dashboard"))

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


@bp.route("/delete/<int:buchung_id>", methods=["POST"])
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

    # Prüfen, ob wir von buchungen-Seite kommen (anhand des return_to Parameters)
    return_to = request.args.get("return_to", "")
    
    if return_to == "buchungen":
        return redirect(
            url_for(
                "dashboard.buchungen",
                year=request.args.get("year"),
                month=request.args.getlist("month"),
                page=request.args.get("page", 1),
                konto=request.args.get("konto", ""),
                kategorie_filter=request.args.get("kategorie_filter", ""),
                kategorie2_filter=request.args.get("kategorie2_filter", ""),
                beschreibung_filter=request.args.get("beschreibung_filter", ""),
            )
        )
    else:
        return redirect(
            url_for(
                "dashboard.dashboard",
                year=request.args.get("year"),
                month=request.args.getlist("month"),
                page=request.args.get("page", 1),
            )
        )
