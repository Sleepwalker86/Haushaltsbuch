import json
import os
import mysql.connector


def load_db_config():
    """Liest die DB-Konfiguration aus config.json neben diesem Skript."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.json")
    with open(cfg_path, "r") as f:
        cfg = json.load(f)
    return cfg["DB_CONFIG"]


def get_connection():
    """Stellt eine neue DB-Verbindung her."""
    db_config = load_db_config()
    return mysql.connector.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
    )

