-- Migration 003: Beleg-Upload-Funktion hinzufügen
-- Fügt ein Feld für den Pfad zu hochgeladenen Belegen (Fotos/PDFs) hinzu

-- Füge beleg_pfad Feld zur buchungen Tabelle hinzu
-- NULL erlaubt, da bestehende Buchungen noch keinen Beleg haben
-- Verwende FIRST statt AFTER, um Kompatibilitätsprobleme zu vermeiden
ALTER TABLE buchungen 
ADD COLUMN beleg_pfad VARCHAR(500) DEFAULT NULL;

-- Optional: Index für schnelleres Suchen nach Buchungen mit Belegen
-- MySQL 8.0+ unterstützt IF NOT EXISTS bei CREATE INDEX
CREATE INDEX IF NOT EXISTS idx_buchungen_beleg_pfad ON buchungen(beleg_pfad);
