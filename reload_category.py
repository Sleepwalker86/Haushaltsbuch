import mysql.connector
import re

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
def normalize_text(text):
    """Text bereinigen: alle Leerzeichen, Tabs, Zeilenumbrüche -> 1 Leerzeichen"""
    if not text:
        return ""
    return " ".join(text.split())

def get_kategorie(text, kat_map):
    """Kategorie anhand der Schlüsselwörter bestimmen"""
    text_lower = text.lower()
    for key, kat in kat_map.items():
        pattern = r'\b' + re.escape(key.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return kat
    return "Sonstiges"

# =============================
# DB VERBINDUNG
# =============================
db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()

# Kategorien laden
cursor.execute("SELECT schluesselwort, kategorie FROM kategorien")
kat_map = dict(cursor.fetchall())

# Alle Buchungen laden
cursor.execute("SELECT id, beschreibung FROM buchungen")
buchungen = cursor.fetchall()

update_count = 0
for b_id, beschreibung in buchungen:
    beschreibung_norm = normalize_text(beschreibung)
    kategorie = get_kategorie(beschreibung_norm, kat_map)

    # Update durchführen
    cursor.execute("UPDATE buchungen SET kategorie=%s WHERE id=%s AND manually_edit IS NULL OR manually_edit=0", (kategorie, b_id))
    update_count += 1

db.commit()
cursor.close()
db.close()

print(f"✅ Kategorieabgleich abgeschlossen: {update_count} Buchungen aktualisiert.")
