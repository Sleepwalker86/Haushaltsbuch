# Datenbank-Migrationen

Dieser Ordner enthält alle Datenbank-Migrationen für die Finanzapp.

## Wie funktioniert es?

Beim Start der Anwendung (sowohl im Docker-Container als auch bei lokaler Installation) wird automatisch geprüft, welche Migrationen noch nicht angewendet wurden. Fehlende Migrationen werden automatisch ausgeführt.

## Neue Migration erstellen

1. **Nummerierung**: Migrationen müssen mit einer Nummer beginnen (z.B. `001_`, `002_`, `003_`)
2. **Dateiname**: Format: `NNN_beschreibung.sql` (z.B. `002_add_user_table.sql`)
3. **SQL-Datei**: Enthält die SQL-Statements für die Migration

### Beispiel

```sql
-- migrations/002_add_user_table.sql
CREATE TABLE IF NOT EXISTS users (
  id INT(11) NOT NULL AUTO_INCREMENT,
  username VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Wichtige Regeln

- ✅ Verwende `CREATE TABLE IF NOT EXISTS` für neue Tabellen
- ✅ Verwende `ALTER TABLE` für Änderungen an bestehenden Tabellen
- ✅ Verwende `IF NOT EXISTS` bei Indizes, um Fehler bei wiederholter Ausführung zu vermeiden
- ✅ Teste Migrationen immer zuerst auf einer Test-Datenbank
- ❌ **NIEMALS** Daten löschen oder bestehende Spalten ohne Backup entfernen
- ❌ **NIEMALS** Migrationen umbenennen oder löschen, die bereits in Produktion angewendet wurden

## Migrationen manuell ausführen

Falls du eine Migration manuell testen möchtest:

```bash
python migrate.py
```

## Aktueller Status

Die Migrationen werden in der Tabelle `schema_migrations` gespeichert. Du kannst den Status prüfen mit:

```sql
SELECT * FROM schema_migrations ORDER BY version;
```
