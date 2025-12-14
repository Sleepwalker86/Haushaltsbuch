import camelot
import mysql.connector
from datetime import datetime
import re
import os
import shutil

# =============================
# RELATIVE PFADDEFINITON
# =============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Projektstammverzeichnis
IMPORT_DIR = os.path.join(BASE_DIR, "import")
IMPORTED_DIR = os.path.join(BASE_DIR, "imported")

# =============================
# DB KONFIGURATION
# =============================
DB_CONFIG = {
    "host": "192.168.10.99",
    "user": "smo",
    "password": "1234",
    "database": "Haushaltsbuch"
}

# =============================
# HILFSFUNKTIONEN
# =============================
def parse_geldwert(text):
    if text is None or text.strip() == "":
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None

def flush_current(current, buchungen):
    if current["datum"] is not None:
        buchungen.append(current.copy())
    current["datum"] = None
    current["art"] = None
    current["beschreibung"] = ""
    current["soll"] = None
    current["haben"] = None
    current["kategorie"] = None
    current["konto"] = None

def normalize_text(text):
    if not text:
        return ""
    return " ".join(text.split())

def get_kategorie(text, kat_map):
    text_lower = text.lower()
    for key, kat in kat_map.items():
        pattern = r'\b' + re.escape(key.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return kat
    return "Sonstiges"

def extract_kontonummer(text):
    match = re.search(r"\b\d{8,}\b", text)  # mindestens 8 Ziffern
    if match:
        return match.group(0)
    return None

def parse_art(text):
    """Art korrekt parsen: erstes Wort, Ausnahme 'Geldautomat'"""
    if not text:
        return ""
    if "geldautomat" in text.lower():
        return "Geldautomat"
    return text.split()[0]

# =============================
# VERBINDUNG ZU MYSQL
# =============================
db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()

# Kategorien aus DB laden
cursor.execute("SELECT schluesselwort, kategorie FROM kategorien")
kat_map = dict(cursor.fetchall())

# =============================
# PDF-Dateien im Import-Ordner verarbeiten
# =============================
pdf_files = [f for f in os.listdir(IMPORT_DIR) if f.lower().endswith(".pdf")]

for pdf_file in pdf_files:
    pdf_path = os.path.join(IMPORT_DIR, pdf_file)
    print(f"📄 Lese PDF: {pdf_file} ...")
    
    try:
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
        if len(tables) == 0:
            print(f"⚠️ Keine Tabellen gefunden: {pdf_file}")
            continue

        df = tables[0].df

        # Kontonummer aus PDF extrahieren (erste Zeilen durchsuchen)
        konto = None
        for i in range(min(5, len(df))):
            konto = extract_kontonummer(str(df.iloc[i,0]))
            if konto:
                break

        header_index = df[df[0].str.contains("Datum", na=False)].index[0]
        df = df.iloc[header_index + 1:].reset_index(drop=True)
        df.columns = ["col1", "soll", "haben"]

        buchungen = []
        current = {"datum": None, "art": None, "beschreibung": "", "soll": None, "haben": None, "kategorie": None, "konto": konto}
        date_regex = re.compile(r"\d{2}\.\d{2}\.\d{4}")

        # ZEILEN PARSEN
        for idx, row in df.iterrows():
            text = str(row["col1"]).strip()
            soll = str(row["soll"]).strip() if row["soll"] else ""
            haben = str(row["haben"]).strip() if row["haben"] else ""

            if date_regex.match(text):
                flush_current(current, buchungen)
                try:
                    parsed_date = datetime.strptime(text.split()[0], "%d.%m.%Y").date()
                except:
                    continue
                current["datum"] = parsed_date

                # Art nach dem Datum extrahieren
                rest_text = text[len(text.split()[0]):].strip()
                current["art"] = parse_art(rest_text)
                current["beschreibung"] = ""
                current["soll"] = parse_geldwert(soll)
                current["haben"] = parse_geldwert(haben)
                current["konto"] = konto
            else:
                if text:
                    current["beschreibung"] += " " + text
                if soll:
                    current["soll"] = parse_geldwert(soll)
                if haben:
                    current["haben"] = parse_geldwert(haben)

        flush_current(current, buchungen)
        print(f"📦 {len(buchungen)} Buchungen erkannt.")

        # EINTRÄGE IN DB EINFÜGEN
        INSERT_SQL = """
        INSERT INTO buchungen (datum, art, beschreibung, soll, haben, kategorie, konto)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        count = 0
        for b in buchungen:
            beschreibung_norm = normalize_text(b["beschreibung"])
            kategorie = get_kategorie(beschreibung_norm, kat_map)

            # Prüfen, ob die Buchung bereits existiert
            cursor.execute("""
                SELECT COUNT(*) FROM buchungen
                WHERE datum=%s AND art=%s AND beschreibung=%s AND soll=%s AND haben=%s AND konto=%s
            """, (b["datum"], b["art"], beschreibung_norm, b["soll"], b["haben"], konto))

            if cursor.fetchone()[0] == 0:
                cursor.execute(INSERT_SQL, (
                    b["datum"],
                    b["art"],
                    beschreibung_norm,
                    b["soll"],
                    b["haben"],
                    kategorie,
                    konto
                ))
                count += 1

        db.commit()
        print(f"🎉 {count} neue Buchungen aus {pdf_file} gespeichert!")

        # PDF in "imported" verschieben
        os.makedirs(IMPORTED_DIR, exist_ok=True)
        shutil.move(pdf_path, os.path.join(IMPORTED_DIR, pdf_file))

    except Exception as e:
        print(f"❌ Fehler beim Verarbeiten von {pdf_file}: {e}")

cursor.close()
db.close()
print("✅ Alle PDFs verarbeitet.")
