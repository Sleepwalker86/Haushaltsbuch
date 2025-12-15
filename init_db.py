import mysql.connector

from db import get_connection, load_db_config


DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS buchungen (
      id INT(11) NOT NULL AUTO_INCREMENT,
      datum DATE NOT NULL,
      art VARCHAR(100) DEFAULT NULL,
      beschreibung TEXT DEFAULT NULL,
      soll DECIMAL(10,2) DEFAULT NULL,
      haben DECIMAL(10,2) DEFAULT NULL,
      erzeugt_am TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
      kategorie VARCHAR(255) DEFAULT NULL,
      kategorie2 VARCHAR(255) DEFAULT NULL,
      konto VARCHAR(50) DEFAULT NULL,
      betrag DECIMAL(10,2) GENERATED ALWAYS AS (IFNULL(haben,0) - IFNULL(soll,0)) STORED,
      gegen_iban VARCHAR(34) DEFAULT NULL,
      manually_edit INT(1) DEFAULT NULL,
      PRIMARY KEY (id),
      UNIQUE KEY unique_buchung (datum, art, beschreibung, soll, haben) USING HASH
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS kategorien (
      id INT(11) NOT NULL AUTO_INCREMENT,
      schluesselwort VARCHAR(255) NOT NULL,
      kategorie VARCHAR(255) NOT NULL,
      PRIMARY KEY (id),
      UNIQUE KEY schluesselwort (schluesselwort)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS konten (
      id INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
      name VARCHAR(100) NOT NULL,
      beschreibung VARCHAR(255) DEFAULT NULL,
      iban VARCHAR(34) DEFAULT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uniq_konten_name (name),
      UNIQUE KEY uniq_konten_iban (iban)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
]


def main():
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

    # Jetzt mit der eigentlichen DB verbinden und Tabellen anlegen
    conn = get_connection()
    try:
        cur = conn.cursor()
        for stmt in DDL_STATEMENTS:
            cur.execute(stmt)
        conn.commit()
        print("✅ Datenbanktabellen wurden angelegt/geprüft.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()


