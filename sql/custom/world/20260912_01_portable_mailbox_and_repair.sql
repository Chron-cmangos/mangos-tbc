-- Custom TBC utilities only. Preserve native spell definitions and creature templates.
-- Spell 1206 is an existing instant, self-target dummy in the 2.4.3 client.
-- Its separate ID keeps the mailbox cooldown independent of the auctioneer.
UPDATE item_template SET spellid_1=1206 WHERE entry=65000 AND spellid_1=30524;

INSERT INTO spell_scripts (Id, ScriptName)
SELECT 1206, 'spell_mantech_portable_mailbox'
WHERE NOT EXISTS (SELECT 1 FROM spell_scripts WHERE Id=1206);

INSERT INTO spell_scripts (Id, ScriptName)
SELECT 44389, 'spell_mantech_portable_repair'
WHERE NOT EXISTS (SELECT 1 FROM spell_scripts WHERE Id=44389);
