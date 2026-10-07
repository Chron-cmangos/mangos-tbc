/*
  CMaNGOS TBC -> WotLK single-character copy
  ------------------------------------------------------------
  Target: current stock CMaNGOS mangos-tbc and mangos-wotlk
  Database: MySQL 5.7+/8.0 or MariaDB 10.2+

  IMPORTANT
  - Back up both character databases before using this file.
  - Stop the destination WotLK world server while executing the copy.
  - The source character must be logged out.
  - All databases must be reachable through this ONE SQL connection.
  - Run once with @execute_copy = 0. Review the validation result.
  - Change @execute_copy to 1 only when the displayed source and
    destination information is correct. Leave @commit_copy at 0 for
    a complete rollback test, then set it to 1 for the real copy.

  Copied:
  - character identity/state fields shared by both schemas
  - home bind
  - equipped gear, backpack, bags, bank, bank bags, and keyring
  - item instances, with newly allocated item GUIDs
  - spells that exist in the destination world database
  - active/rewarded quest data that exists in the destination world DB
  - skills/professions, reputation, and safe spell/item action buttons
  - declined-name data when supported by both databases

  Intentionally not copied:
  - guild/arena membership, mail, auctions, friends, groups
  - pets, auras, cooldowns, corpse data, instance/battleground saves
  - account-wide UI data and macros

  This script COPIES. It never deletes or changes the source character.
*/

-- ============================================================
-- USER INPUTS
-- Change only the values in this section for an ordinary run.
-- Database names may contain letters, numbers, and underscores.
-- ============================================================

-- MySQL requires a current database in which to create the temporary
-- procedures. Set this to the same value as @destination_character_db.
USE `characters_wotlk`;

SET @source_character_db       = 'characters_tbc';
SET @source_auth_db            = 'realmd_tbc';
SET @destination_character_db  = 'characters_wotlk';
SET @destination_auth_db       = 'realmd_wotlk';
SET @destination_world_db      = 'mangos_wotlk';

SET @source_character_name     = 'CharacterName';
SET @source_account_name       = 'SOURCEACCOUNT';
SET @destination_account_name  = 'DESTINATIONACCOUNT';

-- Blank means retain the source character name.
SET @destination_character_name = '';

-- Normally 10 for stock CMaNGOS. Match CharactersPerRealm if changed.
SET @maximum_destination_characters = 10;

-- SAFETY SWITCH: 0 = validate only; 1 = run the complete copy logic.
SET @execute_copy = 0;

-- COMMIT SWITCH: 0 = roll the completed copy back; 1 = keep the copy.
-- This is ignored while @execute_copy is 0.
SET @commit_copy = 0;

-- ============================================================
-- IMPLEMENTATION -- do not edit below unless maintaining script.
-- ============================================================

SET @mantech_old_group_concat_max_len = @@SESSION.group_concat_max_len;
SET SESSION group_concat_max_len = 1048576;

DROP PROCEDURE IF EXISTS mantech_tmp_copy_guid_table;
DROP PROCEDURE IF EXISTS mantech_tmp_tbc_to_wotlk;

DELIMITER $$

CREATE PROCEDURE mantech_tmp_copy_guid_table(
    IN p_source_db VARCHAR(64),
    IN p_destination_db VARCHAR(64),
    IN p_table VARCHAR(64),
    IN p_old_guid BIGINT UNSIGNED,
    IN p_new_guid BIGINT UNSIGNED,
    IN p_extra_where LONGTEXT,
    OUT p_rows_copied BIGINT
)
copy_body: BEGIN
    DECLARE v_table_count INT DEFAULT 0;
    DECLARE v_guid_columns INT DEFAULT 0;
    DECLARE v_missing_required INT DEFAULT 0;
    DECLARE v_columns LONGTEXT;
    DECLARE v_expressions LONGTEXT;

    SET p_rows_copied = 0;

    IF p_table IS NULL OR p_table NOT REGEXP '^[0-9A-Za-z_]+$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Unsafe table name.';
    END IF;

    SELECT COUNT(*)
      INTO v_table_count
      FROM information_schema.TABLES
     WHERE (TABLE_SCHEMA = p_source_db OR TABLE_SCHEMA = p_destination_db)
       AND TABLE_NAME = p_table;

    IF v_table_count <> 2 THEN
        LEAVE copy_body;
    END IF;

    SELECT COUNT(*)
      INTO v_guid_columns
      FROM information_schema.COLUMNS
     WHERE (TABLE_SCHEMA = p_source_db OR TABLE_SCHEMA = p_destination_db)
       AND TABLE_NAME = p_table
       AND COLUMN_NAME = 'guid';

    IF v_guid_columns <> 2 THEN
        LEAVE copy_body;
    END IF;

    SELECT COUNT(*)
      INTO v_missing_required
      FROM information_schema.COLUMNS dc
      LEFT JOIN information_schema.COLUMNS sc
        ON sc.TABLE_SCHEMA = p_source_db
       AND sc.TABLE_NAME = dc.TABLE_NAME
       AND sc.COLUMN_NAME = dc.COLUMN_NAME
     WHERE dc.TABLE_SCHEMA = p_destination_db
       AND dc.TABLE_NAME = p_table
       AND sc.COLUMN_NAME IS NULL
       AND dc.IS_NULLABLE = 'NO'
       AND dc.COLUMN_DEFAULT IS NULL
       AND LOWER(dc.EXTRA) NOT LIKE '%auto_increment%'
       AND LOWER(dc.EXTRA) NOT LIKE '%generated%';

    IF v_missing_required > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A destination table has required columns absent from the source schema.';
    END IF;

    SELECT
        GROUP_CONCAT(
            CONCAT('`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        ),
        GROUP_CONCAT(
            CASE
                WHEN LOWER(dc.COLUMN_NAME) = 'guid'
                    THEN CAST(p_new_guid AS CHAR)
                ELSE CONCAT('s.`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            END
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        )
      INTO v_columns, v_expressions
      FROM information_schema.COLUMNS dc
      JOIN information_schema.COLUMNS sc
        ON sc.TABLE_SCHEMA = p_source_db
       AND sc.TABLE_NAME = dc.TABLE_NAME
       AND sc.COLUMN_NAME = dc.COLUMN_NAME
     WHERE dc.TABLE_SCHEMA = p_destination_db
       AND dc.TABLE_NAME = p_table
       AND LOWER(dc.EXTRA) NOT LIKE '%auto_increment%'
       AND LOWER(dc.EXTRA) NOT LIKE '%generated%';

    IF v_columns IS NULL OR v_expressions IS NULL THEN
        LEAVE copy_body;
    END IF;

    SET @mantech_sql = CONCAT(
        'INSERT INTO `', p_destination_db, '`.`', p_table, '` (', v_columns, ') ',
        'SELECT ', v_expressions, ' FROM `', p_source_db, '`.`', p_table, '` s ',
        'WHERE s.`guid` = ', p_old_guid,
        COALESCE(p_extra_where, '')
    );

    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    SET p_rows_copied = ROW_COUNT();
    DEALLOCATE PREPARE mantech_stmt;
END$$

CREATE PROCEDURE mantech_tmp_tbc_to_wotlk()
main: BEGIN
    DECLARE v_source_guid BIGINT UNSIGNED DEFAULT 0;
    DECLARE v_new_guid BIGINT UNSIGNED DEFAULT 0;
    DECLARE v_source_account_id BIGINT UNSIGNED DEFAULT 0;
    DECLARE v_expected_source_account_id BIGINT UNSIGNED DEFAULT 0;
    DECLARE v_destination_account_id BIGINT UNSIGNED DEFAULT 0;
    DECLARE v_source_online INT DEFAULT 0;
    DECLARE v_source_name VARCHAR(64) DEFAULT '';
    DECLARE v_destination_name VARCHAR(64) DEFAULT '';
    DECLARE v_count BIGINT DEFAULT 0;
    DECLARE v_char_rows BIGINT DEFAULT 0;
    DECLARE v_homebind_rows BIGINT DEFAULT 0;
    DECLARE v_item_rows BIGINT DEFAULT 0;
    DECLARE v_inventory_rows BIGINT DEFAULT 0;
    DECLARE v_spell_rows BIGINT DEFAULT 0;
    DECLARE v_quest_rows BIGINT DEFAULT 0;
    DECLARE v_skill_rows BIGINT DEFAULT 0;
    DECLARE v_reputation_rows BIGINT DEFAULT 0;
    DECLARE v_action_rows BIGINT DEFAULT 0;
    DECLARE v_declined_rows BIGINT DEFAULT 0;
    DECLARE v_lock_name VARCHAR(64) DEFAULT '';
    DECLARE v_lock_acquired INT DEFAULT 0;
    DECLARE v_transaction_started INT DEFAULT 0;
    DECLARE v_columns LONGTEXT;
    DECLARE v_expressions LONGTEXT;
    DECLARE v_missing_required INT DEFAULT 0;
    DECLARE v_extra_source_filter VARCHAR(255) DEFAULT '';
    DECLARE v_result VARCHAR(80) DEFAULT '';

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        IF v_transaction_started = 1 THEN
            ROLLBACK;
        END IF;
        DROP TEMPORARY TABLE IF EXISTS mantech_tmp_item_map;
        DROP TEMPORARY TABLE IF EXISTS mantech_tmp_bag_map;
        IF v_lock_acquired = 1 THEN
            DO RELEASE_LOCK(v_lock_name);
        END IF;
        RESIGNAL;
    END;

    -- Validate configuration values before using them as SQL identifiers.
    IF @source_character_db IS NULL
       OR @source_character_db NOT REGEXP '^[0-9A-Za-z_]+$'
       OR @source_auth_db IS NULL
       OR @source_auth_db NOT REGEXP '^[0-9A-Za-z_]+$'
       OR @destination_character_db IS NULL
       OR @destination_character_db NOT REGEXP '^[0-9A-Za-z_]+$'
       OR @destination_auth_db IS NULL
       OR @destination_auth_db NOT REGEXP '^[0-9A-Za-z_]+$'
       OR @destination_world_db IS NULL
       OR @destination_world_db NOT REGEXP '^[0-9A-Za-z_]+$' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Database names may contain only letters, numbers, and underscores.';
    END IF;

    IF @source_character_db = @destination_character_db THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Source and destination character databases must be different.';
    END IF;

    IF @execute_copy NOT IN (0, 1) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '@execute_copy must be either 0 or 1.';
    END IF;

    IF @commit_copy NOT IN (0, 1) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = '@commit_copy must be either 0 or 1.';
    END IF;

    IF @source_character_name IS NULL OR TRIM(@source_character_name) = ''
       OR @source_account_name IS NULL OR TRIM(@source_account_name) = ''
       OR @destination_account_name IS NULL OR TRIM(@destination_account_name) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Character and account names are required.';
    END IF;

    -- Verify that all five configured databases exist.
    SELECT COUNT(DISTINCT SCHEMA_NAME)
      INTO v_count
      FROM information_schema.SCHEMATA
     WHERE SCHEMA_NAME IN (
        @source_character_db,
        @source_auth_db,
        @destination_character_db,
        @destination_auth_db,
        @destination_world_db
     );

    -- This comparison also handles configurations that reuse one auth database.
    SELECT COUNT(DISTINCT configured_name)
      INTO @mantech_distinct_database_count
      FROM (
          SELECT @source_character_db AS configured_name
          UNION SELECT @source_auth_db
          UNION SELECT @destination_character_db
          UNION SELECT @destination_auth_db
          UNION SELECT @destination_world_db
      ) configured;

    IF v_count <> @mantech_distinct_database_count THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'One or more configured databases do not exist on this MySQL server.';
    END IF;

    -- Required stock CMaNGOS tables.
    SELECT
        (SELECT COUNT(*) FROM information_schema.TABLES
          WHERE TABLE_SCHEMA = @source_character_db
            AND TABLE_NAME IN ('characters', 'character_inventory', 'item_instance'))
      + (SELECT COUNT(*) FROM information_schema.TABLES
          WHERE TABLE_SCHEMA = @destination_character_db
            AND TABLE_NAME IN ('characters', 'character_inventory', 'item_instance'))
      + (SELECT COUNT(*) FROM information_schema.TABLES
          WHERE TABLE_SCHEMA = @source_auth_db AND TABLE_NAME = 'account')
      + (SELECT COUNT(*) FROM information_schema.TABLES
          WHERE TABLE_SCHEMA = @destination_auth_db AND TABLE_NAME = 'account')
      + (SELECT COUNT(*) FROM information_schema.TABLES
          WHERE TABLE_SCHEMA = @destination_world_db
            AND TABLE_NAME IN ('item_template', 'spell_template', 'quest_template'))
      INTO v_count;

    IF v_count <> 11 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A required stock CMaNGOS table is missing.';
    END IF;

    -- Find and verify the source auth account.
    SET @mantech_sql = CONCAT(
        'SELECT COUNT(*), COALESCE(MAX(`id`), 0) ',
        'INTO @mantech_source_account_count, @mantech_source_auth_id ',
        'FROM `', @source_auth_db, '`.`account` ',
        'WHERE `username` = UPPER(', QUOTE(TRIM(@source_account_name)), ')'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;

    IF @mantech_source_account_count <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The source account username was not found exactly once.';
    END IF;
    SET v_expected_source_account_id = @mantech_source_auth_id;

    -- Deleted-character filtering is conditional for older schemas.
    SELECT COUNT(*)
      INTO v_count
      FROM information_schema.COLUMNS
     WHERE TABLE_SCHEMA = @source_character_db
       AND TABLE_NAME = 'characters'
       AND COLUMN_NAME = 'deleteDate';
    IF v_count = 1 THEN
        SET v_extra_source_filter = ' AND (`deleteDate` IS NULL OR `deleteDate` = 0)';
    ELSE
        SET v_extra_source_filter = '';
    END IF;

    SET @mantech_sql = CONCAT(
        'SELECT COUNT(*), COALESCE(MAX(`guid`), 0), COALESCE(MAX(`account`), 0), ',
        'COALESCE(MAX(`online`), 0), COALESCE(MAX(`name`), '''') ',
        'INTO @mantech_source_character_count, @mantech_source_guid, ',
        '@mantech_source_character_account, @mantech_source_online, @mantech_source_name ',
        'FROM `', @source_character_db, '`.`characters` ',
        'WHERE `name` = ', QUOTE(TRIM(@source_character_name)),
        v_extra_source_filter
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;

    IF @mantech_source_character_count <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The active source character was not found exactly once.';
    END IF;

    SET v_source_guid = @mantech_source_guid;
    SET v_source_account_id = @mantech_source_character_account;
    SET v_source_online = @mantech_source_online;
    SET v_source_name = @mantech_source_name;

    IF v_source_account_id <> v_expected_source_account_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The source character does not belong to the configured source account.';
    END IF;

    IF v_source_online <> 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The source character is online. Log it out before copying.';
    END IF;

    -- Resolve the destination account by username. IDs do not need to match.
    SET @mantech_sql = CONCAT(
        'SELECT COUNT(*), COALESCE(MAX(`id`), 0) ',
        'INTO @mantech_destination_account_count, @mantech_destination_auth_id ',
        'FROM `', @destination_auth_db, '`.`account` ',
        'WHERE `username` = UPPER(', QUOTE(TRIM(@destination_account_name)), ')'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;

    IF @mantech_destination_account_count <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The destination account username was not found exactly once.';
    END IF;
    SET v_destination_account_id = @mantech_destination_auth_id;

    SET v_destination_name = TRIM(COALESCE(@destination_character_name, ''));
    IF v_destination_name = '' THEN
        SET v_destination_name = v_source_name;
    END IF;

    IF CHAR_LENGTH(v_destination_name) < 2
       OR CHAR_LENGTH(v_destination_name) > 12
       OR v_destination_name NOT REGEXP '^[A-Za-z]+$' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The destination character name must contain 2-12 letters.';
    END IF;

    -- Preflight name and account-limit checks.
    SET @mantech_sql = CONCAT(
        'SELECT COUNT(*) INTO @mantech_destination_name_count ',
        'FROM `', @destination_character_db, '`.`characters` ',
        'WHERE `name` = ', QUOTE(v_destination_name)
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;

    IF @mantech_destination_name_count <> 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'That character name already exists in the destination database.';
    END IF;

    SET @mantech_sql = CONCAT(
        'SELECT COUNT(*) INTO @mantech_destination_character_count ',
        'FROM `', @destination_character_db, '`.`characters` ',
        'WHERE `account` = ', v_destination_account_id,
        ' AND (`deleteDate` IS NULL OR `deleteDate` = 0)'
    );

    SELECT COUNT(*)
      INTO v_count
      FROM information_schema.COLUMNS
     WHERE TABLE_SCHEMA = @destination_character_db
       AND TABLE_NAME = 'characters'
       AND COLUMN_NAME = 'deleteDate';
    IF v_count = 0 THEN
        SET @mantech_sql = CONCAT(
            'SELECT COUNT(*) INTO @mantech_destination_character_count ',
            'FROM `', @destination_character_db, '`.`characters` ',
            'WHERE `account` = ', v_destination_account_id
        );
    END IF;

    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;

    IF @mantech_destination_character_count >= @maximum_destination_characters THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The destination account is already at its character limit.';
    END IF;

    -- A useful validation-only summary. No destination data has changed yet.
    IF @execute_copy = 0 THEN
        SELECT
            'VALIDATION PASSED - no data was copied' AS result,
            @source_character_db AS source_character_database,
            v_source_name AS source_character,
            v_source_guid AS source_guid,
            v_source_account_id AS source_account_id,
            @destination_character_db AS destination_character_database,
            v_destination_name AS destination_character,
            v_destination_account_id AS destination_account_id,
            @destination_world_db AS destination_world_database,
            'Set @execute_copy = 1 and run the whole file again to copy.' AS next_step;
        LEAVE main;
    END IF;

    -- This lock protects concurrent runs of this script. The destination world
    -- server must still be stopped so it cannot allocate GUIDs simultaneously.
    SET v_lock_name = CONCAT('cmangos_copy_', @destination_character_db);
    SELECT GET_LOCK(v_lock_name, 30) INTO v_lock_acquired;
    IF v_lock_acquired <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Could not obtain the destination copy lock.';
    END IF;

    START TRANSACTION;
    SET v_transaction_started = 1;

    -- Recheck the name under the copy lock.
    SET @mantech_sql = CONCAT(
        'SELECT COUNT(*) INTO @mantech_destination_name_count ',
        'FROM `', @destination_character_db, '`.`characters` ',
        'WHERE `name` = ', QUOTE(v_destination_name), ' FOR UPDATE'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;
    IF @mantech_destination_name_count <> 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The destination name became unavailable before the copy began.';
    END IF;

    SET @mantech_sql = CONCAT(
        'SELECT COALESCE(MAX(`guid`), 0) + 1 INTO @mantech_new_character_guid ',
        'FROM `', @destination_character_db, '`.`characters` FOR UPDATE'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;
    SET v_new_guid = @mantech_new_character_guid;

    -- Ensure every destination-only required character field has a default.
    SELECT COUNT(*)
      INTO v_missing_required
      FROM information_schema.COLUMNS dc
      LEFT JOIN information_schema.COLUMNS sc
        ON sc.TABLE_SCHEMA = @source_character_db
       AND sc.TABLE_NAME = 'characters'
       AND sc.COLUMN_NAME = dc.COLUMN_NAME
     WHERE dc.TABLE_SCHEMA = @destination_character_db
       AND dc.TABLE_NAME = 'characters'
       AND sc.COLUMN_NAME IS NULL
       AND dc.IS_NULLABLE = 'NO'
       AND dc.COLUMN_DEFAULT IS NULL
       AND LOWER(dc.EXTRA) NOT LIKE '%auto_increment%'
       AND LOWER(dc.EXTRA) NOT LIKE '%generated%';
    IF v_missing_required > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'WotLK characters has required columns unavailable from the TBC schema.';
    END IF;

    -- Build the characters INSERT from the intersection of both schemas.
    SELECT
        GROUP_CONCAT(
            CONCAT('`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        ),
        GROUP_CONCAT(
            CASE LOWER(dc.COLUMN_NAME)
                WHEN 'guid' THEN CAST(v_new_guid AS CHAR)
                WHEN 'account' THEN CAST(v_destination_account_id AS CHAR)
                WHEN 'name' THEN QUOTE(v_destination_name)
                WHEN 'online' THEN '0'
                WHEN 'logout_time' THEN 'UNIX_TIMESTAMP()'
                WHEN 'deletedate' THEN 'NULL'
                WHEN 'deleteinfos_account' THEN 'NULL'
                WHEN 'deleteinfos_name' THEN 'NULL'
                WHEN 'taximask' THEN "''"
                WHEN 'transguid' THEN '0'
                WHEN 'transport_x' THEN '0'
                WHEN 'transport_y' THEN '0'
                WHEN 'transport_z' THEN '0'
                WHEN 'transport_o' THEN '0'
                WHEN 'equipmentcache' THEN "''"
                WHEN 'at_login' THEN 'COALESCE(s.`at_login`, 0) | 68'
                ELSE CONCAT('s.`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            END
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        )
      INTO v_columns, v_expressions
      FROM information_schema.COLUMNS dc
      JOIN information_schema.COLUMNS sc
        ON sc.TABLE_SCHEMA = @source_character_db
       AND sc.TABLE_NAME = 'characters'
       AND sc.COLUMN_NAME = dc.COLUMN_NAME
     WHERE dc.TABLE_SCHEMA = @destination_character_db
       AND dc.TABLE_NAME = 'characters'
       AND LOWER(dc.EXTRA) NOT LIKE '%auto_increment%'
       AND LOWER(dc.EXTRA) NOT LIKE '%generated%';

    SET @mantech_sql = CONCAT(
        'INSERT INTO `', @destination_character_db, '`.`characters` (', v_columns, ') ',
        'SELECT ', v_expressions, ' FROM `', @source_character_db, '`.`characters` s ',
        'WHERE s.`guid` = ', v_source_guid
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    SET v_char_rows = ROW_COUNT();
    DEALLOCATE PREPARE mantech_stmt;
    IF v_char_rows <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'The destination character row was not inserted.';
    END IF;

    -- Home bind.
    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_homebind', v_source_guid, v_new_guid, '', v_homebind_rows
    );

    -- Build a complete item GUID map first. This two-pass design preserves
    -- container relationships for bags, bank bags, and keyring inventory.
    DROP TEMPORARY TABLE IF EXISTS mantech_tmp_item_map;
    DROP TEMPORARY TABLE IF EXISTS mantech_tmp_bag_map;
    CREATE TEMPORARY TABLE mantech_tmp_item_map (
        sequence_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        old_guid BIGINT UNSIGNED NOT NULL,
        new_guid BIGINT UNSIGNED DEFAULT NULL,
        item_entry INT UNSIGNED NOT NULL,
        PRIMARY KEY (sequence_id),
        UNIQUE KEY uq_old_guid (old_guid),
        UNIQUE KEY uq_new_guid (new_guid)
    ) ENGINE=InnoDB;

    SET @mantech_sql = CONCAT(
        'INSERT INTO mantech_tmp_item_map (`old_guid`, `item_entry`) ',
        'SELECT ci.`item`, ii.`itemEntry` ',
        'FROM `', @source_character_db, '`.`character_inventory` ci ',
        'JOIN `', @source_character_db, '`.`item_instance` ii ON ii.`guid` = ci.`item` ',
        'JOIN `', @destination_world_db, '`.`item_template` wi ON wi.`entry` = ii.`itemEntry` ',
        'WHERE ci.`guid` = ', v_source_guid, ' ',
        'AND (ci.`bag` = 0 OR EXISTS (',
            'SELECT 1 FROM `', @source_character_db, '`.`character_inventory` bp ',
            'JOIN `', @source_character_db, '`.`item_instance` bi ON bi.`guid` = bp.`item` ',
            'JOIN `', @destination_world_db, '`.`item_template` wb ON wb.`entry` = bi.`itemEntry` ',
            'WHERE bp.`guid` = ', v_source_guid, ' AND bp.`item` = ci.`bag`',
        ')) ORDER BY CASE WHEN ci.`bag` = 0 THEN 0 ELSE 1 END, ci.`bag`, ci.`slot`'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;

    SET @mantech_sql = CONCAT(
        'SELECT COALESCE(MAX(`guid`), 0) INTO @mantech_max_item_guid ',
        'FROM `', @destination_character_db, '`.`item_instance` FOR UPDATE'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    DEALLOCATE PREPARE mantech_stmt;

    UPDATE mantech_tmp_item_map
       SET new_guid = @mantech_max_item_guid + sequence_id;

    -- MySQL cannot reference one temporary table twice in the same statement,
    -- so use a second read-only copy for container/bag GUID lookups.
    CREATE TEMPORARY TABLE mantech_tmp_bag_map (
        old_guid BIGINT UNSIGNED NOT NULL,
        new_guid BIGINT UNSIGNED NOT NULL,
        PRIMARY KEY (old_guid),
        UNIQUE KEY uq_new_guid (new_guid)
    ) ENGINE=InnoDB;
    INSERT INTO mantech_tmp_bag_map (old_guid, new_guid)
    SELECT old_guid, new_guid FROM mantech_tmp_item_map;

    -- Insert remapped item_instance rows using columns common to both schemas.
    SELECT
        GROUP_CONCAT(
            CONCAT('`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        ),
        GROUP_CONCAT(
            CASE LOWER(dc.COLUMN_NAME)
                WHEN 'guid' THEN 'm.`new_guid`'
                WHEN 'owner_guid' THEN CAST(v_new_guid AS CHAR)
                WHEN 'creatorguid' THEN CONCAT(
                    'CASE WHEN s.`creatorGuid` = ', v_source_guid,
                    ' THEN ', v_new_guid, ' ELSE 0 END'
                )
                WHEN 'giftcreatorguid' THEN CONCAT(
                    'CASE WHEN s.`giftCreatorGuid` = ', v_source_guid,
                    ' THEN ', v_new_guid, ' ELSE 0 END'
                )
                WHEN 'itemtextid' THEN '0'
                ELSE CONCAT('s.`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            END
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        )
      INTO v_columns, v_expressions
      FROM information_schema.COLUMNS dc
      JOIN information_schema.COLUMNS sc
        ON sc.TABLE_SCHEMA = @source_character_db
       AND sc.TABLE_NAME = 'item_instance'
       AND sc.COLUMN_NAME = dc.COLUMN_NAME
     WHERE dc.TABLE_SCHEMA = @destination_character_db
       AND dc.TABLE_NAME = 'item_instance'
       AND LOWER(dc.EXTRA) NOT LIKE '%auto_increment%'
       AND LOWER(dc.EXTRA) NOT LIKE '%generated%';

    SET @mantech_sql = CONCAT(
        'INSERT INTO `', @destination_character_db, '`.`item_instance` (', v_columns, ') ',
        'SELECT ', v_expressions, ' ',
        'FROM `', @source_character_db, '`.`item_instance` s ',
        'JOIN mantech_tmp_item_map m ON m.`old_guid` = s.`guid`'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    SET v_item_rows = ROW_COUNT();
    DEALLOCATE PREPARE mantech_stmt;

    -- Insert inventory rows after every item has a destination GUID.
    SELECT
        GROUP_CONCAT(
            CONCAT('`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        ),
        GROUP_CONCAT(
            CASE LOWER(dc.COLUMN_NAME)
                WHEN 'guid' THEN CAST(v_new_guid AS CHAR)
                WHEN 'item' THEN 'm.`new_guid`'
                WHEN 'bag' THEN 'CASE WHEN s.`bag` = 0 THEN 0 ELSE bm.`new_guid` END'
                ELSE CONCAT('s.`', REPLACE(dc.COLUMN_NAME, '`', '``'), '`')
            END
            ORDER BY dc.ORDINAL_POSITION SEPARATOR ', '
        )
      INTO v_columns, v_expressions
      FROM information_schema.COLUMNS dc
      JOIN information_schema.COLUMNS sc
        ON sc.TABLE_SCHEMA = @source_character_db
       AND sc.TABLE_NAME = 'character_inventory'
       AND sc.COLUMN_NAME = dc.COLUMN_NAME
     WHERE dc.TABLE_SCHEMA = @destination_character_db
       AND dc.TABLE_NAME = 'character_inventory'
       AND LOWER(dc.EXTRA) NOT LIKE '%auto_increment%'
       AND LOWER(dc.EXTRA) NOT LIKE '%generated%';

    SET @mantech_sql = CONCAT(
        'INSERT INTO `', @destination_character_db, '`.`character_inventory` (', v_columns, ') ',
        'SELECT ', v_expressions, ' ',
        'FROM `', @source_character_db, '`.`character_inventory` s ',
        'JOIN mantech_tmp_item_map m ON m.`old_guid` = s.`item` ',
        'LEFT JOIN mantech_tmp_bag_map bm ON bm.`old_guid` = s.`bag` ',
        'WHERE s.`guid` = ', v_source_guid,
        ' AND (s.`bag` = 0 OR bm.`new_guid` IS NOT NULL)'
    );
    PREPARE mantech_stmt FROM @mantech_sql;
    EXECUTE mantech_stmt;
    SET v_inventory_rows = ROW_COUNT();
    DEALLOCATE PREPARE mantech_stmt;

    IF v_item_rows <> v_inventory_rows THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Item/inventory row counts differ; the transaction was rolled back.';
    END IF;

    -- Spells existing in WotLK. Talent data is deliberately not translated;
    -- at_login includes RESET_TALENTS so WotLK rebuilds a valid talent state.
    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_spell', v_source_guid, v_new_guid,
        CONCAT(
            ' AND EXISTS (SELECT 1 FROM `', @destination_world_db,
            '`.`spell_template` ws WHERE ws.`id` = s.`spell`)'
        ),
        v_spell_rows
    );

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_queststatus', v_source_guid, v_new_guid,
        CONCAT(
            ' AND EXISTS (SELECT 1 FROM `', @destination_world_db,
            '`.`quest_template` wq WHERE wq.`entry` = s.`quest`)'
        ),
        v_count
    );
    SET v_quest_rows = v_quest_rows + v_count;

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_queststatus_rewarded', v_source_guid, v_new_guid,
        CONCAT(
            ' AND EXISTS (SELECT 1 FROM `', @destination_world_db,
            '`.`quest_template` wq WHERE wq.`entry` = s.`quest`)'
        ),
        v_count
    );
    SET v_quest_rows = v_quest_rows + v_count;

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_queststatus_daily', v_source_guid, v_new_guid,
        CONCAT(
            ' AND EXISTS (SELECT 1 FROM `', @destination_world_db,
            '`.`quest_template` wq WHERE wq.`entry` = s.`quest`)'
        ),
        v_count
    );
    SET v_quest_rows = v_quest_rows + v_count;

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_queststatus_weekly', v_source_guid, v_new_guid,
        CONCAT(
            ' AND EXISTS (SELECT 1 FROM `', @destination_world_db,
            '`.`quest_template` wq WHERE wq.`entry` = s.`quest`)'
        ),
        v_count
    );
    SET v_quest_rows = v_quest_rows + v_count;

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_queststatus_monthly', v_source_guid, v_new_guid,
        CONCAT(
            ' AND EXISTS (SELECT 1 FROM `', @destination_world_db,
            '`.`quest_template` wq WHERE wq.`entry` = s.`quest`)'
        ),
        v_count
    );
    SET v_quest_rows = v_quest_rows + v_count;

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_skills', v_source_guid, v_new_guid, '', v_skill_rows
    );

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_reputation', v_source_guid, v_new_guid, '', v_reputation_rows
    );

    -- Only spell and item buttons are portable. Macros are client/account data.
    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_action', v_source_guid, v_new_guid,
        CONCAT(
            ' AND (',
                '(s.`type` = 0 AND EXISTS (SELECT 1 FROM `', @destination_world_db,
                    '`.`spell_template` ws WHERE ws.`id` = s.`action`)) ',
                'OR ',
                '(s.`type` = 128 AND EXISTS (SELECT 1 FROM `', @destination_world_db,
                    '`.`item_template` wi WHERE wi.`entry` = s.`action`))',
            ')'
        ),
        v_action_rows
    );

    CALL mantech_tmp_copy_guid_table(
        @source_character_db, @destination_character_db,
        'character_declinedname', v_source_guid, v_new_guid, '', v_declined_rows
    );

    IF @commit_copy = 1 THEN
        COMMIT;
        SET v_result = 'COPY COMPLETE';
        SET @new_destination_character_guid = v_new_guid;
    ELSE
        ROLLBACK;
        SET v_result = 'FULL COPY TEST PASSED - ALL CHANGES ROLLED BACK';
        SET @new_destination_character_guid = NULL;
    END IF;
    SET v_transaction_started = 0;
    DROP TEMPORARY TABLE IF EXISTS mantech_tmp_item_map;
    DROP TEMPORARY TABLE IF EXISTS mantech_tmp_bag_map;
    DO RELEASE_LOCK(v_lock_name);
    SET v_lock_acquired = 0;

    SELECT
        v_result AS result,
        v_source_name AS source_character,
        v_source_guid AS source_guid,
        v_destination_name AS destination_character,
        v_new_guid AS destination_guid,
        v_destination_account_id AS destination_account_id,
        v_item_rows AS items_copied,
        v_inventory_rows AS inventory_rows_copied,
        v_spell_rows AS spells_copied,
        v_quest_rows AS quest_rows_copied,
        v_skill_rows AS skills_copied,
        v_reputation_rows AS reputations_copied,
        v_action_rows AS action_buttons_copied,
        CASE WHEN @commit_copy = 1
             THEN 'Destination changes committed.'
             ELSE 'No destination changes were kept; set @commit_copy = 1 for the real copy.'
        END AS persistence;
END$$

DELIMITER ;

CALL mantech_tmp_tbc_to_wotlk();

DROP PROCEDURE IF EXISTS mantech_tmp_tbc_to_wotlk;
DROP PROCEDURE IF EXISTS mantech_tmp_copy_guid_table;

SET SESSION group_concat_max_len = @mantech_old_group_concat_max_len;

/*
  After a successful copy:
  1. Start the WotLK world server.
  2. Log into the copied character.
  3. The character is flagged for a talent and taxi-node reset.
  4. Verify equipment, every bag, bank, bank bags, and keyring.

  The new GUID remains available in:
      SELECT @new_destination_character_guid;
*/

