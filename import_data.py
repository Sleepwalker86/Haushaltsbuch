import mysql.connector
from datetime import datetime
import re
import os
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
IMAGE_DIR = os.path.join(BASE_DIR, "image")

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
    if text is None:
        return ""
    # Alles in String wandeln
    text = str(text)
    # pandas-NaN abfangen
    if text.strip().lower() == "nan":
        return ""
    return " ".join(text.split())

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

def send_image_to_paperless(image_path, paperless_url, paperless_token, paperless_document_type_id):
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

        # Dokumententyp optional vergeben
        data = {}
        if paperless_document_type_id:
            data["document_type"] = paperless_document_type_id
        
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
from utils.csv_parser import BankCSVParser

csv_files = [f for f in os.listdir(IMPORT_DIR) if f.lower().endswith(".csv")]

for csv_file in csv_files:
    csv_path = os.path.join(IMPORT_DIR, csv_file)
    print(f"📄 Lese CSV: {csv_file}")

    try:
        # Verwende robusten CSV-Parser
        parser = BankCSVParser(csv_path)
        df, eigene_iban, column_mapping = parser.parse()
        
        print(f"   ✅ Format erkannt:")
        print(f"      - Encoding: {parser.encoding}")
        print(f"      - Trennzeichen: {parser.delimiter}")
        print(f"      - Header-Zeile: {parser.header_row + 1}")
        if eigene_iban:
            print(f"      - IBAN: {eigene_iban}")
        print(f"      - Spalten-Mapping: {column_mapping}")

        count = 0
        error_count = 0

        for _, row in df.iterrows():
            try:
                # Daten extrahieren
                row_data = parser.extract_row_data(row)
                
                # Prüfe ob Datum und Betrag vorhanden
                if row_data['datum'] is None:
                    error_count += 1
                    continue
                
                datum = row_data['datum'].date()
                betrag = row_data['betrag']
                
                # Soll/Haben bestimmen
                if betrag < 0:
                    soll = abs(betrag)
                    haben = 0.0
                else:
                    soll = 0.0
                    haben = betrag
                
                beschreibung = normalize_text(row_data['beschreibung'])
                art = parse_art(row_data['art'])
                kategorie = get_kategorie(beschreibung, kat_map)
                gegen_iban = row_data['gegen_iban']
                konto = row_data['konto'] or eigene_iban or ''
                
                # DUPLIKATSPRÜFUNG
                cursor.execute("""
                    SELECT COUNT(*) FROM buchungen
                    WHERE datum=%s AND beschreibung=%s AND soll=%s AND haben=%s
                    AND konto=%s AND gegen_iban=%s
                """, (datum, beschreibung, soll, haben, konto, gegen_iban))

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
                        konto,
                        gegen_iban
                    ))
                    count += 1
            except Exception as e:
                error_count += 1
                print(f"   ⚠️  Fehler bei Zeile: {e}")
                continue

        db.commit()
        print(f"🎉 {count} Buchungen importiert")
        if error_count > 0:
            print(f"⚠️  {error_count} Zeilen konnten nicht importiert werden")

        # Datei nach erfolgreichem Import löschen
        os.remove(csv_path)
        print(f"🗑️  {csv_file} wurde gelöscht")

    except Exception as e:
        import traceback
        print(f"❌ Fehler beim Verarbeiten von {csv_file}: {e}")
        print(f"   Details: {traceback.format_exc()}")
        # Datei nicht löschen bei Fehler, damit sie manuell geprüft werden kann

cursor.close()
db.close()

print("✅ Alle CSVs verarbeitet.")

# =============================
# PAPERLESS: BILDER SENDEN
# =============================
if PAPERLESS_CONFIG.get("ip") and PAPERLESS_CONFIG.get("token"):
    paperless_url = PAPERLESS_CONFIG["ip"]
    paperless_token = PAPERLESS_CONFIG["token"]
    paperless_document_type_id = PAPERLESS_CONFIG.get("document_type_id")
    
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
            
            if send_image_to_paperless(image_path, paperless_url, paperless_token, paperless_document_type_id):
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
