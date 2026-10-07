-- Realm-local account discovery. Retain the legacy table for rolling upgrades.
CREATE TABLE IF NOT EXISTS account_dungeon_travel (
  account INT UNSIGNED NOT NULL,
  destination VARCHAR(48) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  first_visit BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (account, destination)
) ENGINE=InnoDB;

INSERT INTO account_dungeon_travel (account, destination, first_visit)
SELECT IF(c.account <> 0, c.account, c.deleteInfos_Account), t.destination, MIN(t.first_visit)
FROM character_dungeon_travel t INNER JOIN characters c ON c.guid = t.guid
WHERE c.account <> 0 OR c.deleteInfos_Account > 0
GROUP BY IF(c.account <> 0, c.account, c.deleteInfos_Account), t.destination
ON DUPLICATE KEY UPDATE first_visit = LEAST(account_dungeon_travel.first_visit, VALUES(first_visit));
