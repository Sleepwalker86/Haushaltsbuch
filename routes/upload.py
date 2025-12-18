"""Upload-Routen."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash, url_for
from werkzeug.utils import secure_filename
import os
import subprocess
import sys

bp = Blueprint('upload', __name__)


@bp.route("/upload", methods=["GET"])
def upload():
    """Separate Seite für CSV-Upload und -Verarbeitung."""
    return render_template("upload_data.html")


@bp.route("/paperless", methods=["GET", "POST"])
def paperless():
    if request.method == "POST":
        file = request.files.get("image_file")
        if not file or file.filename == "":
            flash("Bitte ein Bild auswählen oder aufnehmen.", "error")
            return redirect(url_for("upload.paperless"))

        # Erlaubte Bildformate
        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif"}
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            flash("Nur Bilddateien (PDF, JPG, PNG, HEIC) sind erlaubt.", "error")
            return redirect(url_for("upload.paperless"))

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

        return redirect(url_for("upload.paperless"))

    # GET: Seite anzeigen
    return render_template("paperless.html", title="Paperless")


@bp.route("/upload_csv", methods=["POST"])
def upload_csv():
    file = request.files.get("csv_file")
    if not file or file.filename == "":
        flash("Bitte eine CSV-Datei auswählen.", "error")
        return redirect(url_for("upload.upload"))

    filename = os.path.basename(file.filename)
    if not filename.lower().endswith(".csv"):
        flash("Nur CSV-Dateien sind erlaubt.", "error")
        return redirect(url_for("upload.upload"))

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    import_dir = os.path.join(base_dir, "import")
    os.makedirs(import_dir, exist_ok=True)

    target_path = os.path.join(import_dir, filename)
    try:
        file.save(target_path)
        flash(f"Datei '{filename}' wurde nach 'import' hochgeladen.", "success")
        
        # Direkt nach dem Upload import_data.py ausführen
        try:
            subprocess.run([sys.executable, "import_data.py"], check=True, cwd=base_dir)
            flash("Daten wurden automatisch importiert.", "success")
        except subprocess.CalledProcessError as exc:
            flash(f"Datei hochgeladen, aber Fehler beim Import: {exc}", "error")
        except Exception as exc:
            flash(f"Datei hochgeladen, aber Fehler beim Import: {exc}", "error")
    except Exception as exc:
        flash(f"CSV konnte nicht hochgeladen werden: {exc}", "error")

    return redirect(url_for("upload.upload"))
