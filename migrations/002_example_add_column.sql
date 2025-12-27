-- Beispiel-Migration: Neue Spalte hinzufügen
-- Diese Datei dient nur als Beispiel und wird nicht automatisch ausgeführt
-- (da sie mit 002 beginnt, würde sie nach 001 ausgeführt werden)

-- Beispiel: Neue Spalte zu einer bestehenden Tabelle hinzufügen
-- ALTER TABLE buchungen 
-- ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT NULL AFTER beschreibung;

-- Beispiel: Neuen Index hinzufügen
-- CREATE INDEX IF NOT EXISTS idx_buchungen_datum ON buchungen(datum);

-- Beispiel: Neue Tabelle erstellen
-- CREATE TABLE IF NOT EXISTS settings (
--   id INT(11) NOT NULL AUTO_INCREMENT,
--   key_name VARCHAR(100) NOT NULL,
--   value TEXT DEFAULT NULL,
--   updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--   PRIMARY KEY (id),
--   UNIQUE KEY uniq_key_name (key_name)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- WICHTIG: Diese Migration ist auskommentiert und wird nicht ausgeführt.
-- Wenn du eine echte Migration erstellen willst, kopiere diese Datei,
-- benenne sie um (z.B. 002_add_notes_column.sql) und entferne die Kommentare.
