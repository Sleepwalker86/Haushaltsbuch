-- Initiale Datenbankstruktur
-- Diese Migration erstellt alle Basis-Tabellen

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
  UNIQUE KEY unique_buchung (datum, art, beschreibung(255), soll, haben)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS keyword_category (
  id INT(11) NOT NULL AUTO_INCREMENT,
  schluesselwort VARCHAR(255) NOT NULL,
  kategorie VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY schluesselwort (schluesselwort)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS category (
  id INT(11) NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_category_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
