-- Apply to the character database before enabling PlayerTravel.
-- Additive and repeatable; existing character/game data is unchanged.
CREATE TABLE IF NOT EXISTS character_dungeon_travel (
  guid INT UNSIGNED NOT NULL,
  destination VARCHAR(48) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  first_visit BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (guid, destination)
) ENGINE=InnoDB;
