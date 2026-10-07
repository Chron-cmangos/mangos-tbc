SET @Entry := 190010;

INSERT IGNORE INTO `creature_template` (`entry`, `DisplayId1`, `DisplayIdProbability1`, `name`, `subname`, `GossipMenuId`, `minlevel`, `maxlevel`, `faction`, `NpcFlags`, `scale`, `rank`, `DamageSchool`, `MeleeBaseAttackTime`, `RangedBaseAttackTime`, `unitClass`, `unitFlags`, `CreatureType`, `CreatureTypeFlags`, `lootid`, `PickpocketLootId`, `SkinningLootId`, `AIName`, `MovementType`, `RacialLeader`, `RegenerateStats`, `MechanicImmuneMask`, `ExtraFlags`) VALUES
(@Entry, 2240, 100, 'Magister Stellaria', 'Transmogrifier', 0, 60, 60, 35, 1, 1, 0, 0, 2000, 0, 1, 0, 7, 0, 0, 0, 0, '', 0, 0, 1, 0, 0);


INSERT INTO `creature` (`id`, `map`, `spawnMask`, `position_x`, `position_y`, `position_z`, `orientation`, `spawntimesecsmin`, `spawntimesecsmax`, `spawndist`, `MovementType`) SELECT @Entry, 0, 1, -8999.00000000000000000000, 851.19100000000000000000, 29.62100000000000000000, 3.88538000000000000000, 25, 25, 0, 0 WHERE NOT EXISTS (SELECT 1 FROM `creature` WHERE `id`=@Entry AND `map`=0);
INSERT INTO `creature` (`id`, `map`, `spawnMask`, `position_x`, `position_y`, `position_z`, `orientation`, `spawntimesecsmin`, `spawntimesecsmax`, `spawndist`, `MovementType`) SELECT @Entry, 1, 1, 1467.40000000000000000000, -4226.33000000000000000000, 58.99390000000000000000, 1.19063000000000000000, 25, 25, 0, 0 WHERE NOT EXISTS (SELECT 1 FROM `creature` WHERE `id`=@Entry AND `map`=1);
