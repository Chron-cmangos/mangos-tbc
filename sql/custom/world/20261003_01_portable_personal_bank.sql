-- ManTech Portable Bank (personal storage, not a guild bank).
-- Apply only to mangos_tbc. Requires the matching core before the next restart.
-- No direct mail inserts: startup/login grants handle existing, new and copied characters.
-- 7977 is a stock instant self-target dummy with no visual or native script/item binding
-- in the verified realm data. Native uses remain unchanged by the item-gated script.

CREATE TEMPORARY TABLE mantech_bank_ready AS
SELECT (
    EXISTS (SELECT 1 FROM item_template WHERE entry=65000)
    AND EXISTS (SELECT 1 FROM creature_template WHERE Entry=65002)
    AND EXISTS (SELECT 1 FROM spell_template WHERE Id=7977 AND Effect1=3 AND Effect2=0 AND Effect3=0
                AND EffectImplicitTargetA1=1 AND EffectImplicitTargetB1=0 AND CastingTimeIndex=1)
    AND NOT EXISTS (SELECT 1 FROM item_template WHERE entry=65004
                    AND (name<>'Portable Bank' OR spellid_1<>7977))
    AND NOT EXISTS (SELECT 1 FROM creature_template WHERE Entry=65004
                    AND (Name<>'Portable Banker' OR ScriptName<>''))
    AND NOT EXISTS (SELECT 1 FROM spell_scripts WHERE Id=7977 AND ScriptName<>'spell_mantech_portable_bank')
    AND NOT EXISTS (SELECT 1 FROM dbscripts_on_spell WHERE id=7977)
    AND NOT EXISTS (SELECT 1 FROM item_template WHERE entry<>65004
                    AND 7977 IN (spellid_1,spellid_2,spellid_3,spellid_4,spellid_5))
) AS ready;

CREATE TEMPORARY TABLE mantech_bank_item LIKE item_template;
INSERT INTO mantech_bank_item SELECT * FROM item_template WHERE entry=65000;
UPDATE mantech_bank_item SET entry=65004, name='Portable Bank',
    description='Deploys a personal banker for 10 minutes. Reusable. 30 minute cooldown.',
    Flags=32, BuyPrice=0, SellPrice=0, bonding=1, maxcount=1, stackable=1,
    RequiredLevel=1, RequiredSkill=0, RequiredSkillRank=0, requiredspell=0,
    RequiredReputationFaction=0, RequiredReputationRank=0, AllowableClass=-1, AllowableRace=-1,
    spellid_1=7977, spelltrigger_1=0, spellcharges_1=0, spellcooldown_1=1800000,
    spellcategory_1=0, spellcategorycooldown_1=0, spellid_2=0, spellid_3=0, spellid_4=0, spellid_5=0,
    ScriptName='', Duration=0;

CREATE TEMPORARY TABLE mantech_bank_creature LIKE creature_template;
INSERT INTO mantech_bank_creature SELECT * FROM creature_template WHERE Entry=65002;
UPDATE mantech_bank_creature SET Entry=65004, Name='Portable Banker', SubName='Personal Bank',
    NpcFlags=131072, Faction=35, UnitFlags=768, MovementType=0,
    VendorTemplateId=0, EquipmentTemplateId=0, GossipMenuId=0, LootId=0,
    PickpocketLootId=0, SkinningLootId=0, MinLootGold=0, MaxLootGold=0, SpellList=0,
    AIName='NullAI', ScriptName='';

START TRANSACTION;
INSERT INTO item_template SELECT s.* FROM mantech_bank_item s
WHERE (SELECT ready FROM mantech_bank_ready)=1
  AND NOT EXISTS (SELECT 1 FROM item_template WHERE entry=65004);
INSERT INTO creature_template SELECT s.* FROM mantech_bank_creature s
WHERE (SELECT ready FROM mantech_bank_ready)=1
  AND NOT EXISTS (SELECT 1 FROM creature_template WHERE Entry=65004);
INSERT INTO spell_scripts (Id, ScriptName)
SELECT 7977, 'spell_mantech_portable_bank'
WHERE (SELECT ready FROM mantech_bank_ready)=1 AND NOT EXISTS (SELECT 1 FROM spell_scripts WHERE Id=7977);
COMMIT;

-- MigrationReady must be 1. Zero means an absent prerequisite or conflicting custom
-- entry/binding: this script deliberately made no permanent changes in that case.
SELECT ready AS MigrationReady FROM mantech_bank_ready;
SELECT entry,name,Flags,SellPrice,bonding,maxcount,spellid_1,spellcooldown_1 FROM item_template WHERE entry=65004;
SELECT Entry,Name,NpcFlags,Faction,AIName FROM creature_template WHERE Entry=65004;
SELECT Id,ScriptName FROM spell_scripts WHERE Id=7977;
DROP TEMPORARY TABLE mantech_bank_creature;
DROP TEMPORARY TABLE mantech_bank_item;
DROP TEMPORARY TABLE mantech_bank_ready;
