-- Custom reward 65003 in every expansion. Native item 18246 is read-only.
-- Reusable in Classic/TBC/Wrath; does not teach or consume a native mount.
CREATE TEMPORARY TABLE mantech_raptor_reward LIKE item_template;
INSERT INTO mantech_raptor_reward SELECT * FROM item_template WHERE entry=18246;
UPDATE mantech_raptor_reward SET entry=65003, name='ManTech Black War Raptor Whistle',
    description='Reusable. Requires level 40 and Apprentice Riding. Speed increases from 60% to 100% at level 60 with Journeyman Riding.',
    AllowableClass=-1, AllowableRace=-1, RequiredLevel=40, RequiredSkill=762, RequiredSkillRank=75,
    requiredspell=0, requiredhonorrank=0, RequiredCityRank=0, RequiredReputationFaction=0, RequiredReputationRank=0,
    Flags=32, BuyPrice=0, SellPrice=0, maxcount=1, stackable=1, bonding=1,
    spellid_1=22721, spelltrigger_1=0, spellcharges_1=0,
    spellid_2=0, spelltrigger_2=0, spellcharges_2=0,
    spellid_3=0, spellid_4=0, spellid_5=0;
INSERT INTO item_template SELECT reward.* FROM mantech_raptor_reward reward
WHERE NOT EXISTS (SELECT 1 FROM item_template WHERE entry=65003);
DROP TEMPORARY TABLE mantech_raptor_reward;
