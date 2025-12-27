# Release Notes - Version 1.0.1

## 🎉 Neue Features

### Versionsprüfung und Update-Benachrichtigungen
- **System-Tab in den Einstellungen**: Neuer Tab zeigt aktuelle Version und prüft automatisch auf Updates
- **Docker Hub Integration**: Automatische Versionsprüfung über Docker Hub API
- **Update-Benachrichtigungen**: Benutzer werden informiert, wenn eine neuere Version verfügbar ist
- **Update-Anleitung**: Direkte Anweisungen zum Aktualisieren der Docker-Container

### Erweiterte Analyse-Funktionen
- **Kategorien-Analysen**: Detaillierte Aufschlüsselung der Ausgaben nach Kategorien
- **Top-Kategorien nach Ausgaben**: Übersicht der größten Ausgabenposten
- **Anteil je Kategorie (%)**: Prozentuale Verteilung der Ausgaben als Tortendiagramm
- **Jahresvergleich**: Flexibler Vergleich mit auswählbarem Vergleichsjahr (statt nur Vorjahr)

### Verbesserte CSV-Import-Funktionalität
- **Robuster CSV-Parser**: Automatische Erkennung verschiedener Bankformate
- **Automatische Format-Erkennung**:
  - Encoding (UTF-8, Latin-1, Windows-1252, etc.)
  - Trennzeichen (Semikolon, Komma, Tab, Pipe)
  - Spaltennamen (verschiedene Varianten werden erkannt)
  - Datumsformate (DD.MM.YYYY, YYYY-MM-DD, etc.)
  - Betragsformate (deutsche und englische Formate)
- **IBAN-Erkennung**: Automatische Erkennung der eigenen IBAN aus CSV-Dateien
- **Import-Feedback**: Anzeige der Anzahl importierter Buchungen nach dem Upload

### Datenexport und -import
- **CSV-Export aller Buchungen**: Neuer Tab in den Einstellungen zum Exportieren aller Buchungen
- **CSV-Reimport**: Möglichkeit, CSV-Dateien erneut zu importieren
- **Duplikatsprüfung**: Automatische Erkennung und Vermeidung von Duplikaten beim Import

### Verbesserte Filterung
- **Beschreibungssuche**: Neues Suchfeld zum Filtern nach Begriffen in der Beschreibung
- **Erweiterte Filteroptionen**: Kombination mehrerer Filter für präzise Suche

## 🔧 Verbesserungen

### Benutzerfreundlichkeit
- **Intelligente Weiterleitung**: Nach Bearbeitung/Löschen von Buchungen wird korrekt zur vorherigen Seite zurückgeleitet
- **Verbesserte Dokumentation**: README.md wurde benutzerfreundlicher gestaltet
- **Info-Popover**: Erklärungen zu Funktionen direkt in der Oberfläche verfügbar
- **Bildergalerie**: Screenshots in der Dokumentation für bessere Orientierung

### Code-Qualität
- **Modulare Struktur**: Refactoring von `app.py` in separate Route-Module
- **Robuste Fehlerbehandlung**: Verbesserte Fehlermeldungen und Logging
- **Code-Organisation**: Bessere Strukturierung in `routes/`, `services/`, `utils/`

## 🐛 Bugfixes

- **NaN-Werte in Beschreibung**: Korrekte Behandlung leerer CSV-Felder (keine "nan"-Strings mehr)
- **Weiterleitung nach Bearbeitung**: Korrekte Rückkehr zur Buchungen-Seite oder Dashboard je nach Herkunft
- **Docker-Container**: Verbesserte Fehlerbehandlung bei Datenbankverbindungen
- **Einrückung in app.py**: Korrigierte Code-Formatierung

## 📦 Docker & Deployment

### Docker Hub Integration
- **Multi-Architecture Builds**: Unterstützung für AMD64 und ARM64
- **Automatisierte Builds**: Scripts für einfaches Builden und Pushen
- **Docker Compose Templates**: Separate Dateien für interne und externe Datenbanken
- **Verbesserte Dokumentation**: Detaillierte Anleitungen in DOCKER.md und DOCKER_HUB.md

### Container-Verbesserungen
- **Robuste DB-Verbindungstests**: Verbesserte Prüfung bei externen Datenbanken
- **Netzwerk-Diagnose**: Netcat-Tests für bessere Fehlerdiagnose
- **Config.json Regeneration**: Automatische Aktualisierung bei Container-Start

## 📚 Dokumentation

- **Benutzerfreundliche README**: Weniger technische Begriffe, mehr Fokus auf Endbenutzer
- **Bildergalerie**: Screenshots der wichtigsten Funktionen
- **Docker-Anleitungen**: Umfassende Dokumentation für Docker-Setup
- **CSV-Import-Dokumentation**: Detaillierte Beschreibung unterstützter Formate

## 🔄 Technische Details

### Abhängigkeiten
- `packaging>=23.0` für Versionsvergleiche
- `chardet>=5.0.0` für Encoding-Erkennung
- `pandas>=2.0.0` für robuste CSV-Verarbeitung

### Breaking Changes
Keine

### Migration
Keine Migration erforderlich. Einfach auf Version 1.0.1 aktualisieren.

---

**Vollständige Änderungsliste**: Siehe Git-Commits zwischen v1.0.0 und v1.0.1
