import mysql.connector
from datetime import datetime
import re
import os
import shutil
import pandas as pd
import json
import csv
import requests

# =============================
# CONFIG LADEN
# =============================
with open("config.json", "r") as f:
    config = json.load(f)

DB_CONFIG = config["DB_CONFIG"]
PAPERLESS_CONFIG = config.get("PAPERLESS", {})

# =============================
# PFADE
# =============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORT_DIR = os.path.join(BASE_DIR, "import")
IMPORTED_DIR = os.path.join(BASE_DIR, "imported")
IMAGE_DIR = os.path.join(BASE_DIR, "image")

os.makedirs(IMPORTED_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# =============================
# HILFSFUNKTIONEN
# =============================
def parse_betrag(text):
    if not text:
        return 0.0
    text = text.replace("€", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0

def normalize_text(text):
    return " ".join(text.split()) if text else ""

def get_kategorie(text, kat_map):
    t = text.lower()
    for key, kat in kat_map.items():
        if re.search(r"\b" + re.escape(key.lower()) + r"\b", t):
            return kat
    return "Sonstiges"

def parse_art(umsatztyp):
    if "geldautomat" in umsatztyp.lower():
        return "Geldautomat"
    return umsatztyp.split()[0] if umsatztyp else ""

def send_image_to_paperless(image_path, paperless_url, paperless_token):
    """
    Sendet ein Bild an Paperless-ngx über die API.
    Gibt True zurück bei Erfolg, False bei Fehler.
    """
    try:
        # URL normalisieren (trailing slash sicherstellen)
        api_url = paperless_url.rstrip("/") + "/api/documents/post_document/"
        
        headers = {
            "Authorization": f"Token {paperless_token}"
        }

        # Dokumententyp fest vergeben
        data = {
            "document_type": 47
        }
        
        with open(image_path, "rb") as f:
            files = {"document": f}
            response = requests.post(
                api_url,
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code in (200, 201):
            return True
        else:
            print(f"⚠️  Paperless API Fehler (Status {response.status_code}): {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"⚠️  Fehler beim Senden an Paperless: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Unerwarteter Fehler beim Senden an Paperless: {e}")
        return False

# =============================
# DB VERBINDUNG
# =============================
db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()

# Kategorien aus keyword_category-Tabelle laden
cursor.execute("SELECT schluesselwort, kategorie FROM keyword_category")
kat_map = dict(cursor.fetchall())

# =============================
# CSV VERARBEITUNG
# =============================
csv_files = [f for f in os.listdir(IMPORT_DIR) if f.lower().endswith(".csv")]

for csv_file in csv_files:
    csv_path = os.path.join(IMPORT_DIR, csv_file)
    print(f"📄 Lese CSV: {csv_file}")

    try:
        # Datei roh einlesen (für Kopfzeilen)
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        eigene_iban = None
        header_line = None

        for i, line in enumerate(lines):
            clean = line.strip().replace("\ufeff", "")

            if "Girokonto" in clean and ";" in clean:
                eigene_iban = clean.split(";")[1].replace('"', '').strip()

            if "Buchungsdatum" in clean and "Betrag" in clean:
                header_line = i
                break

        if not eigene_iban or header_line is None:
            print("❌ IBAN oder Header nicht gefunden")
            continue

        # CSV ab Header laden
        df = pd.read_csv(
            csv_path,
            sep=";",
            skiprows=header_line,
            quotechar='"',
            encoding="utf-8"
        )

        count = 0

        for _, row in df.iterrows():
            datum = datetime.strptime(row["Buchungsdatum"], "%d.%m.%y").date()
            betrag = parse_betrag(str(row["Betrag (€)"]))

            if betrag < 0:
                soll = abs(betrag)
                haben = 0.0
            else:
                soll = 0.0
                haben = betrag

            beschreibung = normalize_text(
                f"{row.get('Zahlungsempfänger*in','')} {row.get('Verwendungszweck','')}"
            )

            art = parse_art(str(row.get("Umsatztyp", "")))

            # =============================
            # Hier die Änderung: Einzahlungen von Sascha oder Natascha erkennen
            sender = str(row.get("Zahlungspflichtige*r","")).strip()
            empfänger = str(row.get("Zahlungsempfänger*in","")).strip()
            if betrag > 0 and (sender in ["Sascha Moritz", "Natascha Moritz"] or empfänger in ["Sascha Moritz", "Natascha Moritz"]):
                art = "Einzahlung"
            # =============================

            kategorie = get_kategorie(beschreibung, kat_map)
            gegen_iban = row.get("IBAN", "")

            # DUPLIKATSPRÜFUNG
            cursor.execute("""
                SELECT COUNT(*) FROM buchungen
                WHERE datum=%s AND beschreibung=%s AND soll=%s AND haben=%s
                AND konto=%s AND gegen_iban=%s
            """, (datum, beschreibung, soll, haben, eigene_iban, gegen_iban))

            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO buchungen
                    (datum, art, beschreibung, soll, haben, kategorie, konto, gegen_iban)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    datum,
                    art,
                    beschreibung,
                    soll,
                    haben,
                    kategorie,
                    eigene_iban,
                    gegen_iban
                ))
                count += 1

        db.commit()
        print(f"🎉 {count} Buchungen importiert")

        shutil.move(csv_path, os.path.join(IMPORTED_DIR, csv_file))

    except Exception as e:
        print(f"❌ Fehler: {e}")

cursor.close()
db.close()

print("✅ Alle CSVs verarbeitet.")

# =============================
# PAPERLESS: BILDER SENDEN
# =============================
if PAPERLESS_CONFIG.get("ip") and PAPERLESS_CONFIG.get("token"):
    paperless_url = PAPERLESS_CONFIG["ip"]
    paperless_token = PAPERLESS_CONFIG["token"]
    
    # Unterstützte Bildformate
    image_extensions = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".pdf"}
    
    # Alle Bilder im image-Ordner finden
    image_files = [
        f for f in os.listdir(IMAGE_DIR)
        if os.path.splitext(f.lower())[1] in image_extensions
    ]
    
    if image_files:
        print(f"\n📸 {len(image_files)} Bild(er) gefunden, sende an Paperless...")
        
        for image_file in image_files:
            image_path = os.path.join(IMAGE_DIR, image_file)
            print(f"📤 Sende: {image_file}")
            
            if send_image_to_paperless(image_path, paperless_url, paperless_token):
                try:
                    os.remove(image_path)
                    print(f"✅ {image_file} erfolgreich gesendet und gelöscht")
                except Exception as e:
                    print(f"⚠️  {image_file} gesendet, aber konnte nicht gelöscht werden: {e}")
            else:
                print(f"❌ {image_file} konnte nicht gesendet werden, bleibt erhalten")
    else:
        print("\n📸 Keine neuen Bilder gefunden")
else:
    print("\n📸 Paperless-Konfiguration nicht gefunden, überspringe Bild-Upload")
