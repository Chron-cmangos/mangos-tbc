START TRANSACTION;
UPDATE item_template SET spellid_1 = 44389 WHERE entry = 65001 AND spellid_1 = 28020;
DELETE FROM spell_scripts WHERE Id = 28020 AND ScriptName = 'spell_mantech_portable_repair_carrier';
COMMIT;
