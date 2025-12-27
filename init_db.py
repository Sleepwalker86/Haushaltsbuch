import mysql.connector

from db import get_connection, load_db_config


def main():
    """
    Initialisiert die Datenbank:
    1. Erstellt die Datenbank, falls sie nicht existiert
    2. Führt alle ausstehenden Migrationen aus
    """
    # Zuerst sicherstellen, dass die Datenbank existiert
    cfg = load_db_config()
    db_name = cfg["database"]

    # Verbindung ohne Datenbank herstellen, um sie ggf. anzulegen
    server_conn = mysql.connector.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
    )
    try:
        cur = server_conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        server_conn.commit()
        cur.close()
    finally:
        server_conn.close()

    # Führe Migrationen aus (dies erstellt auch die initialen Tabellen)
    print("🔄 Führe Datenbank-Migrationen aus...")
    try:
        from migrate import main as run_migrations
        run_migrations()
        print("✅ Datenbankinitialisierung abgeschlossen.")
    except ImportError:
        print("⚠️  migrate.py nicht gefunden, überspringe Migrationen.")
        print("   (Dies ist normal bei der ersten Installation)")
    except Exception as e:
        print(f"❌ Fehler bei Migrationen: {e}")
        raise


if __name__ == "__main__":
    main()


