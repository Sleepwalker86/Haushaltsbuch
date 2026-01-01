"""Aktions-Routen (Edit, Delete, Import, etc.)."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash, url_for, send_file, abort
import subprocess
import sys
import os

from db import get_connection
from utils.helpers import parse_amount
from utils.csrf import csrf_protect
from utils.beleg_upload import save_beleg, delete_beleg, get_beleg_path
from services.data_service import fetch_categories

bp = Blueprint('actions', __name__)


def has_beleg_pfad_column(conn):
    """Prüft, ob die beleg_pfad Spalte in der buchungen Tabelle existiert."""
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'buchungen' 
            AND COLUMN_NAME = 'beleg_pfad'
        """)
        result = cur.fetchone()[0] > 0
        return result
    finally:
        cur.close()


@bp.route("/reload-categories", methods=["POST"])
@csrf_protect
def reload_categories():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run([sys.executable, "reload_category.py"], check=True, cwd=base_dir)
        flash("Kategorien wurden neu geladen.", "success")
    except subprocess.CalledProcessError as exc:
        flash(f"Fehler beim Neuladen: {exc}", "error")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/import_data", methods=["POST"])
@csrf_protect
def import_data():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run([sys.executable, "import_data.py"], check=True, cwd=base_dir)
        flash("Daten wurden neu eingelesen.", "success")
    except subprocess.CalledProcessError as exc:
        flash(f"Fehler beim lesen der Daten: {exc}", "error")
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/edit/<int:buchung_id>", methods=["GET", "POST"])
@csrf_protect
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

            # Beleg-Upload verarbeiten (falls vorhanden)
            beleg_pfad = None
            beleg_file = request.files.get('beleg_file')
            
            if beleg_file and beleg_file.filename:
                # Prüfe, ob beleg_pfad Spalte existiert
                with get_connection() as conn:
                    if has_beleg_pfad_column(conn):
                        cur = conn.cursor()
                        cur.execute("SELECT beleg_pfad FROM buchungen WHERE id=%s", (buchung_id,))
                        old_beleg = cur.fetchone()
                        cur.close()
                        
                        if old_beleg and old_beleg[0]:
                            # Alten Beleg löschen
                            delete_beleg(old_beleg[0])
                
                # Neuen Beleg speichern
                relative_path, full_path, error = save_beleg(beleg_file, datum, buchung_id)
                
                if error:
                    flash(f"Fehler beim Beleg-Upload: {error}", "error")
                elif relative_path:
                    beleg_pfad = relative_path
                    flash("Beleg erfolgreich hochgeladen.", "success")
            
            # Prüfe ob Beleg gelöscht werden soll
            delete_beleg_flag = request.form.get('delete_beleg') == '1'
            if delete_beleg_flag:
                # Alten Beleg laden und löschen (nur wenn Spalte existiert)
                with get_connection() as conn:
                    if has_beleg_pfad_column(conn):
                        cur = conn.cursor()
                        cur.execute("SELECT beleg_pfad FROM buchungen WHERE id=%s", (buchung_id,))
                        old_beleg = cur.fetchone()
                        cur.close()
                        
                        if old_beleg and old_beleg[0]:
                            delete_beleg(old_beleg[0])
                            beleg_pfad = None  # Beleg wird gelöscht
                            flash("Beleg wurde gelöscht.", "success")
                    else:
                        flash("Beleg-Funktion ist noch nicht verfügbar. Bitte Migration ausführen.", "warning")

            with get_connection() as conn:
                cur = conn.cursor()
                has_beleg_column = has_beleg_pfad_column(conn)
                
                # Beleg-Pfad aktualisieren (auch wenn None, um zu löschen)
                # Nur wenn Spalte existiert
                if has_beleg_column and (beleg_pfad is not None or delete_beleg_flag):
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
                            manually_edit=%s,
                            beleg_pfad=%s
                        WHERE id=%s
                        """,
                        (datum, art, beschreibung, soll, haben, kategorie, kategorie2, manually_edit_flag, beleg_pfad, buchung_id),
                    )
                else:
                    # Beleg-Pfad nicht ändern, wenn kein neuer Upload und kein Lösch-Request
                    # Oder wenn Spalte noch nicht existiert
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
                # Baue Redirect-URL mit allen Filter-Parametern
                # Nur Parameter mit Werten hinzufügen, um URL sauber zu halten
                redirect_params = {}
                if params_source.get("year"):
                    redirect_params["year"] = params_source.get("year")
                if params_source.getlist("month"):
                    redirect_params["month"] = params_source.getlist("month")
                if params_source.get("page"):
                    redirect_params["page"] = params_source.get("page", 1)
                if params_source.get("konto"):
                    redirect_params["konto"] = params_source.get("konto")
                if params_source.get("kategorie_filter"):
                    redirect_params["kategorie_filter"] = params_source.get("kategorie_filter")
                if params_source.get("kategorie2_filter"):
                    redirect_params["kategorie2_filter"] = params_source.get("kategorie2_filter")
                if params_source.get("beschreibung_filter"):
                    redirect_params["beschreibung_filter"] = params_source.get("beschreibung_filter")
                
                return redirect(url_for("dashboard.buchungen", **redirect_params))
            else:
                return redirect(url_for("dashboard.dashboard", year=params_source.get("year"), month=params_source.getlist("month"), page=params_source.get("page", 1)))
        except Exception as exc:
            flash(f"Fehler: {exc}", "error")

    # Buchung laden (inkl. beleg_pfad, falls vorhanden)
    with get_connection() as conn:
        has_beleg_column = has_beleg_pfad_column(conn)
        cur = conn.cursor()
        
        # SQL-Query dynamisch anpassen
        if has_beleg_column:
            cur.execute(
                "SELECT id, datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto, manually_edit, beleg_pfad FROM buchungen WHERE id=%s",
                (buchung_id,),
            )
        else:
            cur.execute(
                "SELECT id, datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto, manually_edit FROM buchungen WHERE id=%s",
                (buchung_id,),
            )
        
        row = cur.fetchone()
        cur.close()
        if not row:
            flash("Buchung nicht gefunden.", "error")
            return redirect(url_for("dashboard.dashboard"))

        beleg_pfad = row[10] if has_beleg_column and len(row) > 10 else None
        
        # Prüfe, ob Beleg-Datei wirklich existiert (falls beleg_pfad vorhanden)
        if beleg_pfad:
            full_path = get_beleg_path(beleg_pfad)
            if not full_path or not os.path.exists(full_path):
                # Datei existiert nicht - bereinige Datenbankeintrag
                from flask import current_app
                current_app.logger.warning(
                    f"Beleg-Datei nicht gefunden für Buchung {buchung_id}: {beleg_pfad}. "
                    f"Bereinige Datenbankeintrag beim Laden."
                )
                try:
                    cur = conn.cursor()
                    cur.execute("UPDATE buchungen SET beleg_pfad = NULL WHERE id = %s", (buchung_id,))
                    conn.commit()
                    cur.close()
                    current_app.logger.info(f"Datenbankeintrag für Buchung {buchung_id} bereinigt (beleg_pfad auf NULL gesetzt)")
                    beleg_pfad = None  # Setze auf None, damit Template es nicht anzeigt
                except Exception as db_error:
                    current_app.logger.error(f"Fehler beim Bereinigen des Datenbankeintrags für Buchung {buchung_id}: {db_error}")
                    conn.rollback()
        
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
            "beleg_pfad": beleg_pfad,  # Bereinigter Wert (None wenn Datei nicht existiert)
        }

    kategorien = fetch_categories()
    return render_template("edit_buchung.html", buchung=buchung, kategorien=kategorien)


@bp.route("/delete/<int:buchung_id>", methods=["POST"])
@csrf_protect
def delete_buchung(buchung_id):
    try:
        # Beleg löschen (falls vorhanden) bevor Buchung gelöscht wird
        with get_connection() as conn:
            if has_beleg_pfad_column(conn):
                cur = conn.cursor()
                cur.execute("SELECT beleg_pfad FROM buchungen WHERE id=%s", (buchung_id,))
                beleg_result = cur.fetchone()
                cur.close()
                
                if beleg_result and beleg_result[0]:
                    delete_beleg(beleg_result[0])
            
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
        # Baue Redirect-URL mit allen Filter-Parametern
        # Nur Parameter mit Werten hinzufügen, um URL sauber zu halten
        redirect_params = {}
        if request.args.get("year"):
            redirect_params["year"] = request.args.get("year")
        if request.args.getlist("month"):
            redirect_params["month"] = request.args.getlist("month")
        if request.args.get("page"):
            redirect_params["page"] = request.args.get("page", 1)
        if request.args.get("konto"):
            redirect_params["konto"] = request.args.get("konto")
        if request.args.get("kategorie_filter"):
            redirect_params["kategorie_filter"] = request.args.get("kategorie_filter")
        if request.args.get("kategorie2_filter"):
            redirect_params["kategorie2_filter"] = request.args.get("kategorie2_filter")
        if request.args.get("beschreibung_filter"):
            redirect_params["beschreibung_filter"] = request.args.get("beschreibung_filter")
        
        return redirect(url_for("dashboard.buchungen", **redirect_params))
    else:
        return redirect(
            url_for(
                "dashboard.dashboard",
                year=request.args.get("year"),
                month=request.args.getlist("month"),
                page=request.args.get("page", 1),
            )
        )


@bp.route("/beleg/<int:buchung_id>")
def download_beleg(buchung_id):
    """
    Lädt den Beleg einer Buchung herunter.
    
    Args:
        buchung_id: ID der Buchung
    
    Returns:
        File-Response oder 404 wenn nicht gefunden
    """
    try:
        with get_connection() as conn:
            # Prüfe, ob beleg_pfad Spalte existiert
            if not has_beleg_pfad_column(conn):
                abort(404, description="Beleg-Funktion ist noch nicht verfügbar. Bitte Migration ausführen.")
            
            cur = conn.cursor()
            cur.execute("SELECT beleg_pfad FROM buchungen WHERE id=%s", (buchung_id,))
            result = cur.fetchone()
            
            if not result or not result[0]:
                cur.close()
                abort(404, description="Kein Beleg für diese Buchung gefunden")
            
            beleg_pfad = result[0]
            full_path = get_beleg_path(beleg_pfad)
            
            # Wenn Datei nicht existiert, bereinige Datenbankeintrag
            if not full_path or not os.path.exists(full_path):
                from flask import current_app
                current_app.logger.warning(
                    f"Beleg-Datei nicht gefunden für Buchung {buchung_id}: {beleg_pfad}. "
                    f"Bereinige Datenbankeintrag."
                )
                
                # Setze beleg_pfad auf NULL in der Datenbank
                try:
                    cur.execute("UPDATE buchungen SET beleg_pfad = NULL WHERE id = %s", (buchung_id,))
                    conn.commit()
                    current_app.logger.info(f"Datenbankeintrag für Buchung {buchung_id} bereinigt (beleg_pfad auf NULL gesetzt)")
                except Exception as db_error:
                    current_app.logger.error(f"Fehler beim Bereinigen des Datenbankeintrags für Buchung {buchung_id}: {db_error}")
                    conn.rollback()
                
                cur.close()
                abort(404, description="Beleg-Datei wurde nicht gefunden. Der Eintrag wurde automatisch bereinigt.")
            
            cur.close()
            
            # Dateiname für Download extrahieren
            filename = os.path.basename(full_path)
            
            # MIME-Type basierend auf Dateiendung bestimmen
            ext = os.path.splitext(filename)[1].lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            mime_type = mime_types.get(ext, 'application/octet-stream')
            
            return send_file(
                full_path,
                as_attachment=True,
                download_name=filename,
                mimetype=mime_type
            )
            
    except Exception as e:
        from flask import current_app, abort
        # Prüfe, ob es bereits ein abort() war (hat status_code Attribut)
        if hasattr(e, 'code'):
            raise  # Re-raise abort exceptions
        current_app.logger.error(f"Fehler beim Download des Belegs {buchung_id}: {e}", exc_info=True)
        abort(500, description="Fehler beim Laden des Belegs")
