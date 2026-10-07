-- Targeted production log repairs; idempotent and expansion-specific.
-- Repair the obsolete trigger name without replacing other bindings.
UPDATE scripted_areatrigger SET ScriptName='at_southwind_tower'
WHERE entry=3146 AND ScriptName='at_hive_tower';

-- Death-event parameters are evaluated on creatures, not quest-bearing players.
UPDATE creature_ai_scripts SET event_param1=0
WHERE id IN(2209501,2230701) AND event_type=6 AND event_param1=10089;
-- Restore the canonical Deeprun Tram graveyard link only if absent.
INSERT INTO game_graveyard_zone (id,ghost_loc,link_kind,faction)
SELECT 107,2257,0,0 WHERE NOT EXISTS(SELECT 1 FROM game_graveyard_zone WHERE ghost_loc=2257 AND link_kind=0 AND faction=0);
UPDATE creature_spell_list SET Flags=Flags|2
WHERE Id=429301 AND Position=4 AND SpellId=9613 AND Flags=0;
