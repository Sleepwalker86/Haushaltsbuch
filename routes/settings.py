"""Settings-Routen."""
from flask import Blueprint, render_template, request, redirect, flash, url_for, Response
from datetime import datetime, date
import csv
from io import StringIO
from werkzeug.utils import secure_filename

from db import get_connection
from utils.helpers import load_config, save_config
from services.data_service import fetch_konten_details, fetch_category_master, fetch_keyword_mappings
from utils.version import CURRENT_VERSION, is_update_available

bp = Blueprint('settings', __name__)


@bp.route("/settings", methods=["GET", "POST"])
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

            return redirect(url_for("settings.settings", tab="konten"))

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

            return redirect(url_for("settings.settings", tab="konten"))

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

            return redirect(url_for("settings.settings", tab="keywords"))

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

            return redirect(url_for("settings.settings", tab="keywords"))

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

            return redirect(url_for("settings.settings", tab="keywords"))

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
                        cur.execute(
                            """
                            DELETE FROM keyword_category
                            WHERE kategorie = (SELECT name FROM category WHERE id=%s)
                            """,
                            (category_id,),
                        )
                        cur.execute(
                            "DELETE FROM category WHERE id=%s",
                            (category_id,),
                        )
                        conn.commit()
                        cur.close()
                    flash("Kategorie wurde gelöscht.", "success")
                except Exception as exc:
                    flash(f"Kategorie konnte nicht gelöscht werden: {exc}", "error")

            return redirect(url_for("settings.settings", tab="keywords"))

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

            return redirect(url_for("settings.settings", tab="paperless"))

    konten = []
    try:
        konten = fetch_konten_details()
    except Exception as exc:
        flash(f"Konten konnten nicht geladen werden (Tabelle vorhanden?): {exc}", "error")

    # Optional: Konto zum Bearbeiten vorselektieren
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

    # Versionsprüfung
    version_info = {
        "current": CURRENT_VERSION,
        "latest": None,
        "update_available": False,
        "error": None
    }
    
    # Versionsprüfung nur bei GET-Request und wenn Tab "system" ist (oder beim ersten Laden)
    if request.method == "GET":
        try:
            update_available, latest_version, error = is_update_available()
            version_info["latest"] = latest_version
            version_info["update_available"] = update_available
            version_info["error"] = error
        except Exception as e:
            version_info["error"] = f"Fehler bei Versionsprüfung: {str(e)}"

    active_tab = request.args.get("tab")
    if active_tab not in ("konten", "keywords", "paperless", "export", "system"):
        active_tab = "konten"

    return render_template(
        "settings.html",
        konten=konten,
        edit_konto=edit_konto,
        categories_master=categories_master,
        keyword_mappings=keyword_mappings,
        edit_mapping=edit_mapping,
        paperless_config=paperless_config,
        version_info=version_info,
        active_tab=active_tab,
    )


@bp.route("/settings/export-all")
def export_all_buchungen():
    """Exportiert alle Buchungen als CSV-Datei."""
    sql = """
        SELECT datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto, gegen_iban, erzeugt_am
        FROM buchungen
        ORDER BY datum DESC, id DESC
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()

    # CSV erstellen (deutsches Semikolon-Format)
    output = StringIO()
    writer = csv.writer(output, delimiter=";")

    # Kopfzeile
    writer.writerow(
        [
            "Datum",
            "Art",
            "Beschreibung",
            "Soll",
            "Haben",
            "Kategorie",
            "Unterkategorie",
            "Konto",
            "Gegen-IBAN",
            "Erstellt am",
        ]
    )

    for row in rows:
        (
            datum,
            art,
            beschreibung,
            soll,
            haben,
            kategorie,
            kategorie2,
            konto_val,
            gegen_iban,
            erzeugt_am,
        ) = row

        # Datum formatieren
        if isinstance(datum, (datetime, date)):
            datum_str = datum.strftime("%d.%m.%Y")
        else:
            datum_str = str(datum) if datum is not None else ""

        # Erstellt am formatieren
        if isinstance(erzeugt_am, (datetime, date)):
            erzeugt_am_str = erzeugt_am.strftime("%d.%m.%Y %H:%M:%S")
        else:
            erzeugt_am_str = str(erzeugt_am) if erzeugt_am is not None else ""

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
                gegen_iban or "",
                erzeugt_am_str,
            ]
        )

    csv_data = output.getvalue()
    output.close()

    # Dateiname mit aktuellem Datum
    today = datetime.now().strftime("%Y%m%d")
    filename = f"alle_buchungen_{today}.csv"

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/settings/import", methods=["POST"])
def import_buchungen():
    """Importiert Buchungen aus einer CSV-Datei."""
    if "csv_file" not in request.files:
        flash("Keine Datei ausgewählt.", "error")
        return redirect(url_for("settings.settings", tab="export"))

    file = request.files["csv_file"]
    if file.filename == "":
        flash("Keine Datei ausgewählt.", "error")
        return redirect(url_for("settings.settings", tab="export"))

    if not file.filename.lower().endswith(".csv"):
        flash("Nur CSV-Dateien sind erlaubt.", "error")
        return redirect(url_for("settings.settings", tab="export"))

    try:
        # CSV-Datei einlesen
        content = file.read().decode("utf-8")
        reader = csv.DictReader(StringIO(content), delimiter=";")

        # Erwartete Spalten prüfen
        expected_columns = [
            "Datum",
            "Art",
            "Beschreibung",
            "Soll",
            "Haben",
            "Kategorie",
            "Unterkategorie",
            "Konto",
            "Gegen-IBAN",
        ]
        if not all(col in reader.fieldnames for col in expected_columns):
            flash(
                f"CSV-Datei hat nicht die erwarteten Spalten. Erwartet: {', '.join(expected_columns)}",
                "error",
            )
            return redirect(url_for("settings.settings", tab="export"))

        imported_count = 0
        skipped_count = 0
        error_count = 0

        with get_connection() as conn:
            cur = conn.cursor()

            for row in reader:
                try:
                    # Datum parsen (Format: DD.MM.YYYY)
                    datum_str = row["Datum"].strip()
                    if not datum_str:
                        error_count += 1
                        continue

                    try:
                        datum = datetime.strptime(datum_str, "%d.%m.%Y").date()
                    except ValueError:
                        # Versuche alternatives Format
                        try:
                            datum = datetime.strptime(datum_str, "%Y-%m-%d").date()
                        except ValueError:
                            error_count += 1
                            continue

                    # Beträge parsen (deutsches Format: Komma als Dezimaltrennzeichen)
                    soll_str = row["Soll"].strip().replace(".", "").replace(",", ".")
                    haben_str = row["Haben"].strip().replace(".", "").replace(",", ".")

                    try:
                        soll = float(soll_str) if soll_str else 0.0
                        haben = float(haben_str) if haben_str else 0.0
                    except ValueError:
                        error_count += 1
                        continue

                    # Textfelder
                    art = row.get("Art", "").strip() or None
                    beschreibung = row.get("Beschreibung", "").strip() or None
                    kategorie = row.get("Kategorie", "").strip() or None
                    kategorie2 = row.get("Unterkategorie", "").strip() or None
                    konto = row.get("Konto", "").strip() or None
                    gegen_iban = row.get("Gegen-IBAN", "").strip() or None

                    # Duplikatsprüfung
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM buchungen
                        WHERE datum=%s AND beschreibung=%s AND soll=%s AND haben=%s
                        AND konto=%s AND gegen_iban=%s
                        """,
                        (datum, beschreibung, soll, haben, konto, gegen_iban),
                    )

                    if cur.fetchone()[0] == 0:
                        # Buchung einfügen
                        cur.execute(
                            """
                            INSERT INTO buchungen
                            (datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto, gegen_iban, manually_edit)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (datum, art, beschreibung, soll, haben, kategorie, kategorie2, konto, gegen_iban, 1),
                        )
                        imported_count += 1
                    else:
                        skipped_count += 1

                except Exception as e:
                    error_count += 1
                    continue

            conn.commit()
            cur.close()

        # Erfolgsmeldung
        messages = []
        if imported_count > 0:
            messages.append(f"{imported_count} Buchung(en) erfolgreich importiert.")
        if skipped_count > 0:
            messages.append(f"{skipped_count} Duplikat(e) übersprungen.")
        if error_count > 0:
            messages.append(f"{error_count} Zeile(n) konnten nicht importiert werden.")

        if messages:
            flash(" ".join(messages), "success" if imported_count > 0 else "warning")
        else:
            flash("Keine Buchungen konnten importiert werden.", "error")

    except Exception as exc:
        flash(f"Fehler beim Importieren: {exc}", "error")

    return redirect(url_for("settings.settings", tab="export"))
