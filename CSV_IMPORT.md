# CSV-Import - Unterstützte Bankformate

Das `import_data.py` Script unterstützt jetzt verschiedene CSV-Formate von verschiedenen Banken.

## Automatische Erkennung

Das Script erkennt automatisch:

- **Encoding**: UTF-8, Latin-1, Windows-1252, etc.
- **Trennzeichen**: Semikolon (`;`), Komma (`,`), Tab (`\t`), Pipe (`|`)
- **Spaltennamen**: Verschiedene Varianten werden automatisch erkannt
- **Datumsformate**: DD.MM.YYYY, DD.MM.YY, YYYY-MM-DD, etc.
- **Betragsformate**: Deutsche (1.234,56) und englische (1,234.56) Formate

## Unterstützte Spaltennamen

Das Script erkennt folgende Spaltennamen automatisch:

### Datum
- `Buchungsdatum`, `Datum`, `Buchungstag`, `Wertstellung`, `Wertstellungsdatum`, `Valutadatum`, `Date`, `Transaction Date`

### Betrag
- `Betrag (€)`, `Betrag`, `Umsatz`, `Amount`, `Betrag in EUR`, `Betrag in €`

### Empfänger/Zahlungsempfänger
- `Zahlungsempfänger*in`, `Zahlungsempfänger`, `Empfänger`, `Empfänger*in`, `Zahlungsempfänger/in`, `Name`, `Auftraggeber`, `Begünstigter`, `Payee`, `Recipient`

### Verwendungszweck
- `Verwendungszweck`, `Verwendungszweck/Zweck`, `Zweck`, `Buchungstext`, `Buchungstext/Verwendungszweck`, `Text`, `Bemerkung`, `Notiz`, `Description`, `Memo`, `Note`, `Reference`

### IBAN
- `IBAN`, `Gegenkonto`, `Kontonummer`, `Empfänger IBAN`, `Zahlungsempfänger IBAN`, `Account`, `Account Number`

### Art/Umsatztyp
- `Umsatztyp`, `Art`, `Typ`, `Transaction Type`, `Buchungsart`, `Transaktionstyp`, `Type`, `Category`

## Unterstützte Datumsformate

- `DD.MM.YYYY` (z.B. 01.12.2024)
- `DD.MM.YY` (z.B. 01.12.24)
- `YYYY-MM-DD` (z.B. 2024-12-01)
- `DD/MM/YYYY` (z.B. 01/12/2024)
- `DD/MM/YY` (z.B. 01/12/24)
- `YYYY/MM/DD` (z.B. 2024/12/01)
- `DD-MM-YYYY` (z.B. 01-12-2024)
- `DD-MM-YY` (z.B. 01-12-24)

## Unterstützte Betragsformate

- Deutsche Format: `1.234,56` oder `-85,40`
- Englisches Format: `1,234.56` oder `-85.40`
- Einfach: `1234.56` oder `-85.40`
- Mit Währungssymbol: `€ 1.234,56` oder `$ 1,234.56`

## IBAN-Erkennung

Das Script sucht automatisch nach der eigenen IBAN in:
- Zeilen mit "Girokonto", "IBAN", "Kontonummer", "Account"
- Nach Doppelpunkt, Semikolon oder Gleichheitszeichen

## Beispiel-CSV-Formate

### Format 1: Deutsche Bank (Standard)
```csv
Girokonto;DE12345678901234567890
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Umsatztyp;IBAN;Betrag (€)
01.12.24;01.12.24;Gebucht;ISSUER;REWE;Einkauf;Ausgang;DE96120300009005290904;-85,40
```

### Format 2: ING / Comdirect
```csv
Buchungsdatum;Wertstellung;Status;Zahlungsempfänger;Verwendungszweck;Umsatztyp;IBAN;Betrag
01.12.2024;01.12.2024;Gebucht;REWE;Einkauf;Ausgang;DE96120300009005290904;-85,40
```

### Format 3: Sparkasse
```csv
Buchungstag;Wertstellung;Umsatzart;Zahlungsempfänger/Zahlungsempfängerin;Verwendungszweck;IBAN;Betrag in EUR
01.12.2024;01.12.2024;Lastschrift;REWE;Einkauf;DE96120300009005290904;-85,40
```

## Fehlerbehandlung

- **Unbekannte Spalten**: Das Script versucht, die wichtigsten Spalten (Datum, Betrag) zu finden. Fehlende Spalten werden ignoriert.
- **Fehlerhafte Zeilen**: Zeilen mit Fehlern werden übersprungen, aber die Datei wird nicht gelöscht.
- **Encoding-Probleme**: Automatische Erkennung mit Fallback auf Latin-1.

## Neue Bankformate hinzufügen

Falls ein Bankformat nicht erkannt wird, können Sie die Spaltennamen in `utils/csv_parser.py` erweitern:

```python
COLUMN_MAPPINGS = {
    "standard": {
        "datum": ["Buchungsdatum", "Datum", ...],  # Hier neue Namen hinzufügen
        "betrag": ["Betrag (€)", "Betrag", ...],   # Hier neue Namen hinzufügen
        # ...
    }
}
```

## Debugging

Bei Problemen mit einem CSV-Format:

1. Prüfen Sie die Logs - das Script zeigt erkannte Formate an
2. Prüfen Sie die Spaltennamen in Ihrer CSV-Datei
3. Fügen Sie fehlende Spaltennamen zu `COLUMN_MAPPINGS` hinzu
4. Testen Sie mit einer kleinen CSV-Datei zuerst

## Bekannte unterstützte Banken

- Deutsche Bank
- ING
- Comdirect
- Sparkasse
- DKB (Deutsche Kreditbank)
- Volksbanken
- Raiffeisenbanken

Falls Ihre Bank nicht funktioniert, bitte die CSV-Struktur (erste Zeilen) teilen, dann kann das Format hinzugefügt werden.
