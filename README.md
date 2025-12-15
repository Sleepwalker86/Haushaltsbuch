# Haushaltsbuch – PDF/CSV zu Dashboard

## Übersicht

Dieses Projekt ist ein persönliches Haushaltsbuch, das Bankumsätze aus CSV-Dateien einliest, strukturiert in eine MySQL/MariaDB-Datenbank speichert und sie anschließend in einer responsiven Web-App visualisiert.

Die Weboberfläche (Flask + Bootstrap) bietet:

- Manuelles Erfassen von Buchungen (z. B. Barzahlungen)
- Automatisierten CSV-Import (z. B. aus Online-Banking-Exporten)
- Kategorisierung von Umsätzen (inkl. Unterkategorie)
- Dashboard mit Diagrammen (Kategorien, Ausgaben, Einzahlungen)
- Verwaltung von Konten (Name, IBAN, Beschreibung)
- Zeitgesteuerten Import über systemd-Timer auf dem Server

---

## Funktionen im Detail

### Dashboard (`/dashboard`)

- **Filter**: Jahr, Monat, Konto (IBAN), Unterkategorie (Freitext).
- **Diagramme (Chart.js)**:
  - Kategorien (Einnahmen/Ausgaben) als gestapeltes Balkendiagramm inkl. Summen (gesamt Einnahmen/Ausgaben).
  - Ausgaben (Kategorien) als Tortendiagramm.
  - Einzahlungen nach IBAN als Balkendiagramm.
- **Buchungstabelle**:
  - Spalten: Datum, Art, Beschreibung, Soll, Haben, Kategorie, Unterkategorie.
  - Paginierung (30 Einträge pro Seite).
  - Bearbeiten-Button je Buchung → `/edit/<id>`.

### Buchung erfassen (`/`)

- Felder:
  - Datum
  - Typ (Ausgaben / Einnahmen)
  - Konto (Dropdown aus `konten`-Tabelle, Pflichtfeld)
  - Kategorie (Dropdown aus `kategorien`-Tabelle)
  - Unterkategorie (`kategorie2`, Freitext)
  - Betrag (Komma/Punkt als Dezimaltrenner)
  - Beschreibung
- Speicherung:
  - Tabelle `buchungen`
  - Ausgaben → `soll`, Einnahmen → `haben`
  - `manually_edit = 1` zur Kennzeichnung manueller Einträge.

### Buchung bearbeiten / löschen (`/edit/<id>`, `/delete/<id>`)

- Bearbeiten:
  - Alle Felder der Buchung änderbar.
  - Beim Speichern wird `manually_edit = 1` gesetzt.
- Löschen:
  - Separater Button mit Sicherheitsabfrage (`confirm`).
  - Löscht aus `buchungen` und leitet zurück ins Dashboard inkl. Filter.

### Einstellungen & Kontenverwaltung (`/settings`)

Zwei Tabs:

- **CSV Upload & Import**
  - CSV-Datei hochladen (`/upload_csv`): Datei wird in den Ordner `import/` gespeichert.
  - Buttons:
    - „Kategorien neu laden“ → ruft `reload_category.py` auf.
    - „CSV Daten einlesen“ → ruft `import_data.py` auf.

- **Konten & Einstellungen**
  - Konto anlegen/bearbeiten:
    - Name
    - Beschreibung
    - IBAN
  - Liste vorhandener Konten aus Tabelle `konten` mit Bearbeiten-Icon:
    - Klick lädt das Konto in das Formular zum Editieren (selber Tab).

---

## Technische Anforderungen

- **Betriebssystem**: Debian/Ubuntu mit systemd (getestet auf Debian 12)
- **Python**: 3.11
- **Datenbank**: MySQL oder MariaDB (z. B. MariaDB 10.x)
- **Pakete (in venv)**:
  - `flask`
  - `mysql-connector-python`
  - `pandas`
  - `python-dateutil`
- **Systempakete**:
  - `python3`, `python3-venv`, `python3-pip`
  - `mariadb-client`
  - `git`, `curl`, `ca-certificates`

---

## Installation (Server)

### 1. Repository nach `/opt` klonen

```bash
sudo git clone https://github.com/Sleepwalker86/Haushaltsbuch.git /opt/finanzapp
cd /opt/finanzapp
```

### 2. Installationsscript ausführen

```bash
sudo chmod +x install.sh
sudo ./install.sh
```

Das Script erledigt:

1. `apt update` und Installation der Systempakete.
2. Anlage des Users `finanzapp` (falls nicht vorhanden).
3. Klonen/Update des Repos unter `/opt/finanzapp` (als User `finanzapp`).
4. Anlage der Ordner `import/` und `imported/`.
5. Erzeugung einer Python-virtualenv unter `/opt/finanzapp/venv`.
6. Installation der Python-Abhängigkeiten in der venv.
7. Anlegen von `config.json` (falls nicht vorhanden) mit interaktiver Abfrage von:
   - DB-Host
   - DB-User
   - DB-Passwort
   - DB-Name
8. Anlegen und Aktivieren der systemd-Units:
   - `finanzapp.service` – startet die Flask-App (Produktionsmodus, kein Debug).
   - `finanzapp-import.service` – einmaliger CSV-Import via `import_data.py`.
   - `finanzapp-import.timer` – ruft den Import-Service alle 10 Minuten auf.

### 3. Services prüfen

```bash
systemctl status finanzapp.service
systemctl status finanzapp-import.timer
```

Die App ist i. d. R. unter `http://SERVER-IP:5001` erreichbar.

---

## Lokale Entwicklung

### 1. Klonen & venv

```bash
git clone https://github.com/Sleepwalker86/Haushaltsbuch.git
cd Haushaltsbuch

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. `config.json` anlegen (lokal)

```json
{
  "DB_CONFIG": {
    "host": "127.0.0.1",
    "user": "dein_user",
    "password": "dein_passwort",
    "database": "Haushaltsbuch"
  }
}
```

### 3. App lokal starten

```bash
export FLASK_DEBUG=1
python app.py
```

Dann ist die App unter `http://127.0.0.1:5001` erreichbar.

---

## Nutzung

1. **Einstellungen → Konten**: Konten anlegen (Name, IBAN, Beschreibung).
2. **CSV Upload**:
   - Im Tab „Upload“ CSV hochladen (landet im `import/`-Ordner).
   - „CSV Daten einlesen“ ausführen oder Timer abwarten.
3. **Dashboard** ansehen und filtern:
   - Jahr, Monat, Konto, Unterkategorie.
4. **Buchungen manuell erfassen** unter `/`.
5. **Buchungen bearbeiten oder löschen** über die Tabelle im Dashboard.

---

## Lizenz / Nutzung

© 2025 Sascha Moritz

Der Quellcode darf für den **eigenen Gebrauch** angepasst und erweitert werden.

Eine **Weitergabe, Veröffentlichung oder kommerzielle Nutzung veränderter Versionen ist nicht gestattet**.

Wenn du den Code in einem anderen Kontext einsetzen willst (z. B. in einem Unternehmen oder als Open‑Source‑Projekt), kläre dies bitte vorher mit dem Autor.

---

## Haftungsausschluss

Dieses Projekt wird ohne Garantie bereitgestellt. Es gibt keine Gewähr für Richtigkeit, Vollständigkeit oder Eignung für einen bestimmten Zweck. Die Nutzung erfolgt auf eigene Verantwortung – insbesondere im Hinblick auf den Umgang mit sensiblen Finanzdaten.
