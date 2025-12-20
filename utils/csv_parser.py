"""Robuster CSV-Parser für verschiedene Bankformate."""
import pandas as pd
import csv
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import chardet


class BankCSVParser:
    """Parser für verschiedene Bank-CSV-Formate."""
    
    # Bekannte Spaltennamen-Mappings für verschiedene Banken
    COLUMN_MAPPINGS = {
        # Standard deutsche Banken (Comdirect, ING, Sparkasse, etc.)
        "standard": {
            "datum": ["Buchungsdatum", "Datum", "Buchungstag", "Wertstellung", "Wertstellungsdatum", "Valutadatum", "date", "Date"],
            "betrag": ["Betrag (€)", "Betrag", "Umsatz", "Amount", "amount", "Betrag in EUR", "Betrag in €"],
            "empfaenger": ["Zahlungsempfänger*in", "Zahlungsempfänger", "Empfänger", "Empfänger*in", "Zahlungsempfänger/in", "Name", "name", "Auftraggeber", "Begünstigter"],
            "verwendungszweck": ["Verwendungszweck", "Verwendungszweck/Zweck", "Zweck", "Buchungstext", "Buchungstext/Verwendungszweck", "Text", "text", "Bemerkung", "Notiz"],
            "iban": ["IBAN", "iban", "Gegenkonto", "Kontonummer", "Empfänger IBAN", "Zahlungsempfänger IBAN"],
            "art": ["Umsatztyp", "Art", "Typ", "Transaction Type", "type", "Buchungsart", "Transaktionstyp"],
            "konto": ["Konto", "Kontonummer", "Von Konto", "Eigenes Konto"]
        },
        # Alternative Formate
        "alternative": {
            "datum": ["Transaction Date", "Date", "date", "Datum", "Buchungsdatum"],
            "betrag": ["Amount", "amount", "Betrag", "Umsatz", "Value"],
            "empfaenger": ["Payee", "Recipient", "Name", "Description", "Payee Name"],
            "verwendungszweck": ["Description", "Memo", "Note", "Reference", "Details"],
            "iban": ["Account", "Account Number", "IBAN"],
            "art": ["Type", "Category", "Transaction Type"],
            "konto": ["Account", "From Account"]
        }
    }
    
    # Bekannte Datumsformate
    DATE_FORMATS = [
        "%d.%m.%Y",      # 01.12.2024
        "%d.%m.%y",      # 01.12.24
        "%Y-%m-%d",      # 2024-12-01
        "%d/%m/%Y",      # 01/12/2024
        "%d/%m/%y",      # 01/12/24
        "%Y/%m/%d",      # 2024/12/01
        "%d-%m-%Y",      # 01-12-2024
        "%d-%m-%y",      # 01-12-24
    ]
    
    def __init__(self, csv_path: str):
        """
        Initialisiert den Parser für eine CSV-Datei.
        
        Args:
            csv_path: Pfad zur CSV-Datei
        """
        self.csv_path = csv_path
        self.encoding = None
        self.delimiter = None
        self.header_row = None
        self.column_mapping = {}
        self.eigene_iban = None
        self.df = None
        
    def detect_encoding(self) -> str:
        """Erkennt die Encoding der Datei."""
        with open(self.csv_path, 'rb') as f:
            raw_data = f.read(10000)  # Erste 10KB lesen
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            # Fallback auf utf-8 wenn unsicher
            if result.get('confidence', 0) < 0.7:
                encoding = 'utf-8'
        return encoding
    
    def detect_delimiter(self, sample_lines: List[str]) -> str:
        """Erkennt das Trennzeichen (Semikolon, Komma, Tab)."""
        # Prüfe verschiedene Trennzeichen
        delimiters = [';', ',', '\t', '|']
        delimiter_counts = {}
        
        for delimiter in delimiters:
            count = 0
            for line in sample_lines[:5]:  # Erste 5 Zeilen prüfen
                count += line.count(delimiter)
            delimiter_counts[delimiter] = count
        
        # Nehme Trennzeichen mit den meisten Vorkommen
        if delimiter_counts:
            detected = max(delimiter_counts.items(), key=lambda x: x[1])
            if detected[1] > 0:
                return detected[0]
        
        return ';'  # Standard: Semikolon
    
    def find_column_mapping(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Findet die Spalten-Mappings basierend auf verfügbaren Spaltennamen.
        
        Returns:
            Dict mit Mapping: {interner_name: tatsächlicher_spaltenname}
        """
        mapping = {}
        df_columns_lower = [col.lower().strip() for col in df.columns]
        
        # Durchsuche alle bekannten Mappings
        for mapping_set in self.COLUMN_MAPPINGS.values():
            for internal_name, possible_names in mapping_set.items():
                for possible_name in possible_names:
                    # Exakte Übereinstimmung (case-insensitive)
                    if possible_name.lower() in df_columns_lower:
                        idx = df_columns_lower.index(possible_name.lower())
                        mapping[internal_name] = df.columns[idx]
                        break
                    # Teilübereinstimmung
                    for col in df.columns:
                        if possible_name.lower() in col.lower() or col.lower() in possible_name.lower():
                            mapping[internal_name] = col
                            break
                    if internal_name in mapping:
                        break
        
        return mapping
    
    def find_header_row(self, lines: List[str]) -> Tuple[Optional[int], Optional[str]]:
        """
        Findet die Header-Zeile und erkennt das Trennzeichen.
        
        Returns:
            Tuple: (header_row_index, delimiter)
        """
        # Erkenne Trennzeichen aus ersten Zeilen
        delimiter = self.detect_delimiter(lines[:10])
        
        # Suche nach Header-Zeile (enthält typische Spaltennamen)
        header_keywords = [
            "buchungsdatum", "datum", "betrag", "empfänger", "verwendungszweck",
            "date", "amount", "payee", "description", "transaction"
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Prüfe ob Zeile typische Header-Keywords enthält
            keyword_count = sum(1 for keyword in header_keywords if keyword in line_lower)
            if keyword_count >= 2:  # Mindestens 2 Keywords gefunden
                return i, delimiter
        
        return None, delimiter
    
    def find_iban(self, lines: List[str]) -> Optional[str]:
        """Findet die eigene IBAN in den Metadaten-Zeilen."""
        iban_pattern = re.compile(r'[A-Z]{2}\d{2}[A-Z0-9]{4,30}')
        
        for line in lines[:20]:  # Erste 20 Zeilen prüfen
            # Suche nach "Girokonto", "IBAN", "Kontonummer" etc.
            if any(keyword in line.lower() for keyword in ["girokonto", "iban", "kontonummer", "account"]):
                # Extrahiere IBAN
                matches = iban_pattern.findall(line.upper())
                if matches:
                    return matches[0]
                # Fallback: Suche nach IBAN nach Doppelpunkt oder Gleichheitszeichen
                parts = re.split(r'[:;=]', line, maxsplit=1)
                if len(parts) > 1:
                    potential_iban = parts[1].strip().replace('"', '').replace("'", "")
                    if iban_pattern.match(potential_iban):
                        return potential_iban
        
        return None
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Versucht verschiedene Datumsformate zu parsen."""
        if pd.isna(date_str) or not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def parse_amount(self, amount_str: str) -> float:
        """
        Parst Beträge in verschiedenen Formaten.
        Unterstützt: "1.234,56", "1,234.56", "1234.56", "-85,40", etc.
        """
        if pd.isna(amount_str) or not amount_str:
            return 0.0
        
        amount_str = str(amount_str).strip()
        
        # Entferne Währungssymbole
        amount_str = re.sub(r'[€$£]', '', amount_str).strip()
        
        # Entferne Leerzeichen
        amount_str = amount_str.replace(' ', '')
        
        # Prüfe ob negativ
        is_negative = amount_str.startswith('-') or amount_str.startswith('(')
        amount_str = amount_str.lstrip('-(').rstrip(')')
        
        # Erkenne Format: Komma oder Punkt als Dezimaltrennzeichen
        if ',' in amount_str and '.' in amount_str:
            # Beide vorhanden: letztes ist Dezimaltrennzeichen
            if amount_str.rindex(',') > amount_str.rindex('.'):
                # Komma ist Dezimaltrennzeichen, Punkt ist Tausendertrennzeichen
                amount_str = amount_str.replace('.', '').replace(',', '.')
            else:
                # Punkt ist Dezimaltrennzeichen, Komma ist Tausendertrennzeichen
                amount_str = amount_str.replace(',', '')
        elif ',' in amount_str:
            # Nur Komma: könnte Dezimal- oder Tausendertrennzeichen sein
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Dezimaltrennzeichen
                amount_str = amount_str.replace(',', '.')
            else:
                # Tausendertrennzeichen
                amount_str = amount_str.replace(',', '')
        # Punkt bleibt wie er ist (wird als Dezimaltrennzeichen interpretiert)
        
        try:
            value = float(amount_str)
            return -value if is_negative else value
        except ValueError:
            return 0.0
    
    def parse(self) -> Tuple[pd.DataFrame, Optional[str], Dict[str, str]]:
        """
        Parst die CSV-Datei und gibt DataFrame, IBAN und Column-Mapping zurück.
        
        Returns:
            Tuple: (DataFrame, eigene_iban, column_mapping)
        """
        # Encoding erkennen
        self.encoding = self.detect_encoding()
        
        # Datei einlesen
        try:
            with open(self.csv_path, 'r', encoding=self.encoding, errors='ignore') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Fallback auf latin-1
            with open(self.csv_path, 'r', encoding='latin-1', errors='ignore') as f:
                lines = f.readlines()
            self.encoding = 'latin-1'
        
        # BOM entfernen
        if lines:
            lines[0] = lines[0].replace('\ufeff', '')
        
        # IBAN finden
        self.eigene_iban = self.find_iban(lines)
        
        # Header-Zeile finden
        self.header_row, self.delimiter = self.find_header_row(lines)
        
        if self.header_row is None:
            raise ValueError("Header-Zeile konnte nicht gefunden werden")
        
        # DataFrame laden
        try:
            self.df = pd.read_csv(
                self.csv_path,
                sep=self.delimiter,
                skiprows=self.header_row,
                encoding=self.encoding,
                quotechar='"',
                on_bad_lines='skip',
                engine='python'
            )
        except Exception as e:
            # Fallback: Versuche mit anderen Einstellungen
            try:
                self.df = pd.read_csv(
                    self.csv_path,
                    sep=self.delimiter,
                    skiprows=self.header_row,
                    encoding='latin-1',
                    quotechar='"',
                    on_bad_lines='skip',
                    engine='python'
                )
            except Exception:
                raise ValueError(f"CSV konnte nicht gelesen werden: {e}")
        
        # Spalten-Mapping finden
        self.column_mapping = self.find_column_mapping(self.df)
        
        # Prüfe ob mindestens Datum und Betrag gefunden wurden
        if 'datum' not in self.column_mapping:
            raise ValueError("Spalte 'Datum' konnte nicht gefunden werden")
        if 'betrag' not in self.column_mapping:
            raise ValueError("Spalte 'Betrag' konnte nicht gefunden werden")
        
        return self.df, self.eigene_iban, self.column_mapping
    
    def extract_row_data(self, row: pd.Series) -> Dict:
        """
        Extrahiert Daten aus einer DataFrame-Zeile basierend auf dem Column-Mapping.
        
        Returns:
            Dict mit: datum, betrag, beschreibung, art, gegen_iban, konto
        """
        data = {}
        
        # Datum
        if 'datum' in self.column_mapping:
            date_str = row.get(self.column_mapping['datum'], '')
            data['datum'] = self.parse_date(date_str)
        else:
            data['datum'] = None
        
        # Betrag
        if 'betrag' in self.column_mapping:
            betrag_str = row.get(self.column_mapping['betrag'], '')
            data['betrag'] = self.parse_amount(betrag_str)
        else:
            data['betrag'] = 0.0
        
        # Beschreibung (Empfänger + Verwendungszweck)
        empfaenger = ''
        verwendungszweck = ''
        
        if 'empfaenger' in self.column_mapping:
            val = row.get(self.column_mapping['empfaenger'], '')
            if not pd.isna(val):
                empfaenger = str(val).strip()
        
        if 'verwendungszweck' in self.column_mapping:
            val = row.get(self.column_mapping['verwendungszweck'], '')
            if not pd.isna(val):
                verwendungszweck = str(val).strip()
        
        data['beschreibung'] = f"{empfaenger} {verwendungszweck}".strip()
        
        # Art
        if 'art' in self.column_mapping:
            val = row.get(self.column_mapping['art'], '')
            data['art'] = str(val).strip() if not pd.isna(val) else ''
        else:
            data['art'] = ''
        
        # Gegen-IBAN
        if 'iban' in self.column_mapping:
            val = row.get(self.column_mapping['iban'], '')
            data['gegen_iban'] = str(val).strip() if not pd.isna(val) else ''
        else:
            data['gegen_iban'] = ''
        
        # Konto (eigene IBAN oder aus Spalte)
        if 'konto' in self.column_mapping:
            val = row.get(self.column_mapping['konto'], '')
            data['konto'] = str(val).strip() if not pd.isna(val) else (self.eigene_iban or '')
        else:
            data['konto'] = self.eigene_iban or ''
        
        return data
