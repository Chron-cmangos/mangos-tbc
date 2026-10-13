-- All MC encounters grant each eligible raid member one consumable douse.
-- Native ITEM_FLAG_MULTI_DROP: taking your copy does not remove another's.
-- Preserve Unique (MaxCount=1), bonding, single-use charge and all other flags.
UPDATE item_template SET Flags = Flags | 2048 WHERE entry = 17333;

INSERT INTO creature_loot_template
 (entry,item,ChanceOrQuestChance,groupid,mincountOrRef,maxcount,condition_id,comments)
SELECT DISTINCT LootId,17333,100,0,1,1,0,'ManTech: personal Aqual Quintessence for MC dousing'
FROM creature_template
WHERE Entry IN (12118,11982,12259,12057,12056,12264,12098,11988,11502) AND LootId > 0
ON DUPLICATE KEY UPDATE ChanceOrQuestChance=100,groupid=0,mincountOrRef=1,maxcount=1,condition_id=0,comments=VALUES(comments);

-- Majordomo surrenders, so use his reward chest instead of a corpse.
-- Native chest groupLootRules must register the raid before the first loot:
-- otherwise the chest can disappear after the first opener takes their copy.
UPDATE gameobject_template SET data15=1 WHERE entry=179703 AND type=3;
INSERT INTO gameobject_loot_template
 (entry,item,ChanceOrQuestChance,groupid,mincountOrRef,maxcount,condition_id,comments)
SELECT data1,17333,100,0,1,1,0,'ManTech: personal Aqual Quintessence for MC dousing'
FROM gameobject_template WHERE entry=179703 AND type=3 AND data1 > 0
ON DUPLICATE KEY UPDATE ChanceOrQuestChance=100,groupid=0,mincountOrRef=1,maxcount=1,condition_id=0,comments=VALUES(comments);
