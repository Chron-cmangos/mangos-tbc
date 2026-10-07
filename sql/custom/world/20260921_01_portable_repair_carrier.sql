-- Apply to mangos_tbc AFTER installing the matching core, with the world server stopped.
-- Item 65001 only. Native repair items/spells and old script bindings are preserved.
-- 28020 is not used by another item in the verified production data.
START TRANSACTION;
INSERT INTO spell_scripts (Id, ScriptName)
SELECT 28020, 'spell_mantech_portable_repair_carrier'
WHERE NOT EXISTS (SELECT 1 FROM spell_scripts WHERE Id = 28020);

UPDATE item_template
SET spellid_1 = 28020
WHERE entry = 65001 AND spellid_1 IN (44389, 28020)
  AND EXISTS (SELECT 1 FROM spell_scripts WHERE Id = 28020
              AND ScriptName = 'spell_mantech_portable_repair_carrier')
  AND NOT EXISTS (SELECT 1 FROM spell_scripts WHERE Id = 28020
                  AND ScriptName <> 'spell_mantech_portable_repair_carrier');
COMMIT;
-- Verify: item 65001 must show spell 28020 and cooldown 1800000.
SELECT entry, name, spellid_1, spellcooldown_1 FROM item_template WHERE entry = 65001;
SELECT Id, ScriptName FROM spell_scripts WHERE Id = 28020;
