"""Settings-Routen."""
from flask import Blueprint, render_template, request, redirect, flash, url_for

from db import get_connection
from utils.helpers import load_config, save_config
from services.data_service import fetch_konten_details, fetch_category_master, fetch_keyword_mappings

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
