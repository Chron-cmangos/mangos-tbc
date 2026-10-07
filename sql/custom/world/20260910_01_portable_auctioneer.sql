-- Portable Auctioneer: stable item entry 65002 in every expansion.
-- Requires the matching core spell script. Does not mail items to players.
-- No native item, creature or spell definition is changed.
CREATE TEMPORARY TABLE portable_auction_item LIKE item_template;
INSERT INTO portable_auction_item SELECT * FROM item_template WHERE entry=65000;
UPDATE portable_auction_item SET entry=65002, name='Portable Auctioneer',
  description='Deploys a stationary auctioneer for 10 minutes. Reusable. 30 minute cooldown.',
  spellid_1=21342, spelltrigger_1=0, spellcharges_1=0, spellcooldown_1=1800000,
  spellcategory_1=0, spellcategorycooldown_1=0, RequiredSkill=0, RequiredSkillRank=0;
INSERT INTO item_template SELECT s.* FROM portable_auction_item s
WHERE NOT EXISTS (SELECT 1 FROM item_template WHERE entry=65002);
DROP TEMPORARY TABLE portable_auction_item;

CREATE TEMPORARY TABLE portable_auction_creature LIKE creature_template;
INSERT INTO portable_auction_creature SELECT * FROM creature_template WHERE Entry=14337;
UPDATE portable_auction_creature SET Entry=65002, Name='Camotron 9000',
  SubName='Auction House', DisplayId1=6909, DisplayId2=0, DisplayId3=0, DisplayId4=0,
  Faction=35, NpcFlags=2097152, UnitFlags=768, MovementType=0, VendorTemplateId=0,
  EquipmentTemplateId=0, GossipMenuId=0, LootId=0, PickpocketLootId=0, SkinningLootId=0,
  MinLootGold=0, MaxLootGold=0, SpellList=0, AIName='NullAI', ScriptName='';
INSERT INTO creature_template SELECT s.* FROM portable_auction_creature s
WHERE NOT EXISTS (SELECT 1 FROM creature_template WHERE Entry=65002);
DROP TEMPORARY TABLE portable_auction_creature;

-- Carrier 21342 is a client-supported, instant self-target dummy with no visual,
-- native script binding or item use in the validated data. The script gates on
-- item 65002, preserving any non-item/native use of this spell.
INSERT INTO spell_scripts (Id, ScriptName)
SELECT 21342, 'spell_mantech_portable_auctioneer'
WHERE NOT EXISTS (SELECT 1 FROM spell_scripts WHERE Id=21342);
