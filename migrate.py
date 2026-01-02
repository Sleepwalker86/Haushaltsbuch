#!/usr/bin/env python3
"""
Datenbank-Migrationssystem

Dieses Script prüft beim Start, welche Migrationen noch nicht angewendet wurden
und führt sie automatisch aus. Migrationen werden in migrations/ als nummerierte
SQL-Dateien gespeichert (z.B. 001_initial_schema.sql, 002_add_column.sql).
"""

import os
import re
import mysql.connector
from pathlib import Path
from db import get_connection, load_db_config


def get_migration_table(conn):
    """
    Erstellt die schema_migrations Tabelle, falls sie nicht existiert.
    
    Hinweis: Die Tabelle sollte eigentlich bereits durch Migration 001 erstellt werden.
    Diese Funktion dient als Fallback für den Fall, dass die Migration noch nicht
    ausgeführt wurde oder die Tabelle aus anderen Gründen fehlt.
    """
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    conn.commit()
    cur.close()


def get_applied_migrations(conn):
    """Gibt eine Liste aller bereits angewendeten Migrationen zurück."""
    cur = conn.cursor()
    cur.execute("SELECT version FROM schema_migrations ORDER BY version")
    applied = [row[0] for row in cur.fetchall()]
    cur.close()
    return set(applied)


def get_pending_migrations(migrations_dir):
    """Gibt eine sortierte Liste aller verfügbaren Migrationen zurück."""
    if not os.path.exists(migrations_dir):
        return []
    
    migrations = []
    for file in sorted(os.listdir(migrations_dir)):
        if file.endswith('.sql'):
            # Extrahiere Versionsnummer aus Dateinamen (z.B. "001_..." -> "001")
            match = re.match(r'^(\d+)_', file)
            if match:
                version = match.group(1)
                migrations.append({
                    'version': version,
                    'file': file,
                    'path': os.path.join(migrations_dir, file)
                })
    
    return sorted(migrations, key=lambda x: int(x['version']))


def apply_migration(conn, migration):
    """Wendet eine einzelne Migration an."""
    print(f"📝 Wende Migration {migration['version']} an: {migration['file']}")
    
    with open(migration['path'], 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Entferne Kommentare und teile in einzelne Statements
    # Wichtig: Mehrzeilige Statements müssen korrekt behandelt werden
    # Entferne Zeilen-Kommentare
    lines = []
    for line in sql.split('\n'):
        # Entferne Kommentare am Zeilenende
        if '--' in line:
            comment_pos = line.find('--')
            # Prüfe ob es wirklich ein Kommentar ist (nicht in String)
            line = line[:comment_pos].rstrip()
        if line.strip():
            lines.append(line.strip())
    
    # Verbinde Zeilen und teile nach Semikolon
    sql_clean = ' '.join(lines)
    statements = [s.strip() for s in sql_clean.split(';') if s.strip()]
    
    # Prüfe, ob Migration nur Kommentare enthält (z.B. Beispiel-Migrationen)
    # Entferne Statements, die nur aus Kommentaren bestehen
    actual_statements = []
    for stmt in statements:
        # Entferne alle Kommentare aus dem Statement
        stmt_clean = stmt
        if '--' in stmt_clean:
            # Entferne Kommentare am Zeilenende
            stmt_lines = stmt_clean.split('\n')
            cleaned_lines = []
            for line in stmt_lines:
                if '--' in line:
                    comment_pos = line.find('--')
                    line = line[:comment_pos].strip()
                if line.strip():
                    cleaned_lines.append(line.strip())
            stmt_clean = ' '.join(cleaned_lines)
        
        # Wenn nach Entfernen der Kommentare noch SQL-Code übrig ist, ist es ein echtes Statement
        if stmt_clean and not stmt_clean.isspace():
            actual_statements.append(stmt)
    
    # Wenn keine echten Statements vorhanden sind, überspringe die Migration
    if not actual_statements:
        print(f"   ⚠️  Migration {migration['version']} enthält nur Kommentare/Beispiele, überspringe...")
        # Markiere trotzdem als angewendet, damit sie nicht erneut geprüft wird
        description = migration['file'].replace('.sql', '').replace(f"{migration['version']}_", "")
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (%s, %s)",
                (migration['version'], description)
            )
            conn.commit()
            print(f"✅ Migration {migration['version']} als Beispiel-Migration markiert (übersprungen)")
        except mysql.connector.Error as e:
            # Ignoriere Fehler wenn Migration bereits markiert ist
            if e.errno != 1062:  # 1062 = Duplicate entry
                raise
            print(f"   → Migration {migration['version']} war bereits markiert")
        finally:
            cur.close()
        return
    
    # Verwende nur die echten Statements
    statements = actual_statements
    
    print(f"   Gefundene Statements: {len(statements)}")
    for i, stmt in enumerate(statements, 1):
        print(f"   Statement {i}: {stmt[:100]}...")
    
    cur = conn.cursor()
    try:
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    print(f"   → Führe Statement {i}/{len(statements)} aus...")
                    print(f"   SQL: {statement}")
                    cur.execute(statement)
                    affected = cur.rowcount
                    print(f"   ✓ Statement {i} erfolgreich (affected rows: {affected})")
                    # Bei ALTER TABLE sollte rowcount -1 sein (nicht anwendbar)
                    if 'ALTER TABLE' in statement.upper() or 'ADD COLUMN' in statement.upper():
                        print(f"   → ALTER TABLE Statement ausgeführt, prüfe sofort ob Spalte existiert...")
                        # Prüfe sofort nach dem Statement
                        if 'beleg_pfad' in statement.lower():
                            cur.execute("""
                                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                                WHERE TABLE_SCHEMA = DATABASE() 
                                AND TABLE_NAME = 'buchungen' 
                                AND COLUMN_NAME = 'beleg_pfad'
                            """)
                            exists = cur.fetchone()[0] > 0
                            if exists:
                                print(f"   ✓ Spalte beleg_pfad existiert jetzt!")
                            else:
                                print(f"   ❌ Spalte beleg_pfad existiert NICHT nach ALTER TABLE!")
                                print(f"   → Möglicherweise fehlende Berechtigungen oder Tabellen-Sperre")
                except mysql.connector.Error as e:
                    # Prüfe, ob es ein "Duplicate column" oder "Duplicate key" Fehler ist
                    # Diese können ignoriert werden, wenn die Migration bereits teilweise ausgeführt wurde
                    error_code = e.errno
                    error_msg = str(e).lower()
                    
                    # MySQL Fehlercodes:
                    # 1060 = Duplicate column name
                    # 1061 = Duplicate key name
                    # 1054 = Unknown column (kann ignoriert werden bei DROP COLUMN)
                    # 1062 = Duplicate entry (für UNIQUE Constraints)
                    if error_code in (1060, 1061, 1062) or 'duplicate' in error_msg:
                        print(f"   ⚠️  Warnung bei Statement {i}: {e}")
                        print(f"   → Spalte/Index existiert bereits, überspringe...")
                        continue
                    else:
                        # Andere Fehler weiterwerfen mit mehr Details
                        print(f"   ❌ Fehler bei Statement {i}: {e}")
                        print(f"   Fehlercode: {error_code}")
                        print(f"   Statement war: {statement}")
                        raise
        
        # Commit nach allen Statements
        conn.commit()
        print(f"   ✓ Alle Statements erfolgreich ausgeführt")
        
        # Verifiziere, dass die Migration wirklich erfolgreich war
        # Prüfe nur, wenn tatsächlich ein ALTER TABLE Statement mit beleg_pfad ausgeführt wurde
        # (nicht nur wenn es im Kommentar vorkommt)
        migration_successful = True
        beleg_pfad_expected = False
        
        # Prüfe, ob in den tatsächlich ausgeführten Statements (nicht in Kommentaren) 
        # ein ALTER TABLE mit beleg_pfad vorkommt
        for statement in statements:
            statement_clean = statement.upper().strip()
            # Ignoriere Kommentare und leere Statements
            if statement_clean.startswith('--') or not statement_clean:
                continue
            # Prüfe, ob ein ALTER TABLE Statement mit beleg_pfad tatsächlich ausgeführt wurde
            if ('ALTER TABLE' in statement_clean and 
                'ADD COLUMN' in statement_clean and 
                'BELEG_PFAD' in statement_clean):
                beleg_pfad_expected = True
                break
        
        if beleg_pfad_expected:
            print(f"   → Verifiziere, ob Spalte beleg_pfad erstellt wurde...")
            cur.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'buchungen' 
                AND COLUMN_NAME = 'beleg_pfad'
            """)
            column_exists = cur.fetchone()[0] > 0
            if not column_exists:
                print(f"   ❌ FEHLER: Spalte beleg_pfad wurde NICHT erstellt!")
                print(f"   → Prüfe alle Spalten der Tabelle buchungen...")
                cur.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'buchungen'
                    ORDER BY ORDINAL_POSITION
                """)
                columns = [row[0] for row in cur.fetchall()]
                print(f"   Vorhandene Spalten: {', '.join(columns)}")
                print(f"   → Migration wird NICHT als angewendet markiert")
                migration_successful = False
            else:
                print(f"   ✓ Verifikation: Spalte beleg_pfad existiert")
        
        if not migration_successful:
            conn.rollback()
            raise Exception("Migration fehlgeschlagen: Spalte beleg_pfad wurde nicht erstellt. Bitte manuell prüfen.")
        
        # Markiere Migration als angewendet
        description = migration['file'].replace('.sql', '').replace(f"{migration['version']}_", "")
        cur.execute(
            "INSERT INTO schema_migrations (version, description) VALUES (%s, %s)",
            (migration['version'], description)
        )
        conn.commit()
        print(f"✅ Migration {migration['version']} erfolgreich angewendet")
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ Fehler bei Migration {migration['version']}: {e}")
        print(f"   Fehlercode: {e.errno}")
        raise
    finally:
        cur.close()


def main():
    """Hauptfunktion: Prüft und wendet fehlende Migrationen an."""
    print("🔄 Prüfe Datenbank-Migrationen...")
    
    # Verbindung zur Datenbank
    conn = get_connection()
    try:
        # Erstelle Migrations-Tabelle
        get_migration_table(conn)
        
        # Hole bereits angewendete Migrationen
        applied = get_applied_migrations(conn)
        print(f"   Bereits angewendet: {len(applied)} Migration(en)")
        
        # Hole verfügbare Migrationen
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        pending = get_pending_migrations(migrations_dir)
        
        if not pending:
            print("   Keine Migrationen gefunden (migrations/ Ordner existiert nicht oder ist leer)")
            return
        
        # Filtere noch nicht angewendete Migrationen
        to_apply = [m for m in pending if m['version'] not in applied]
        
        if not to_apply:
            print("✅ Datenbank ist auf dem neuesten Stand")
            return
        
        print(f"   {len(to_apply)} neue Migration(en) gefunden")
        
        # Wende Migrationen der Reihe nach an
        for migration in to_apply:
            apply_migration(conn, migration)
        
        print(f"✅ Alle Migrationen erfolgreich angewendet ({len(to_apply)} Migrationen)")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
