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
    """Erstellt die schema_migrations Tabelle, falls sie nicht existiert."""
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
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    cur = conn.cursor()
    try:
        for statement in statements:
            if statement:
                cur.execute(statement)
        
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
