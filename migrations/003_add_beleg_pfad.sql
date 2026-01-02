-- Migration 003: Beleg-Upload-Funktion hinzufügen
-- Fügt ein Feld für den Pfad zu hochgeladenen Belegen (Fotos/PDFs) hinzu

-- Füge beleg_pfad Feld zur buchungen Tabelle hinzu
-- NULL erlaubt, da bestehende Buchungen noch keinen Beleg haben
-- Verwende FIRST statt AFTER, um Kompatibilitätsprobleme zu vermeiden
ALTER TABLE buchungen 
ADD COLUMN beleg_pfad VARCHAR(500) DEFAULT NULL;

-- Optional: Index für schnelleres Suchen nach Buchungen mit Belegen
-- Hinweis: Falls der Index bereits existiert, wird der Fehler 1061 (Duplicate key) 
-- von der Migration-Logik abgefangen und ignoriert
CREATE INDEX idx_buchungen_beleg_pfad ON buchungen(beleg_pfad);
