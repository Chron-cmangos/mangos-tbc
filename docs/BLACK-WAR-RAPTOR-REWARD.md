# ManTech Black War Raptor reward

Custom item **65003**, ManTech Black War Raptor Whistle, uses the existing Black War Raptor appearance. Native item 18246 and spell-template 22721 are unchanged. The original mount's cast requirements and speed are unchanged; the core scales only auras cast from custom item 65003.

The custom whistle is reusable and remains in bags in Classic, TBC and Wrath. It does not teach a mount-journal spell or consume itself in Wrath, preserving the same transfer behavior in every expansion. It is soulbound, unique, unsellable (SellPrice=0) and protected from player destruction (Flags=32), matching the three portable utilities. No additional combat/indoor/cooldown exemptions are granted: ordinary mount-use rules apply.

All races/factions can use it at level 40 with Apprentice Riding (75). It grants no riding skill. Base mounted speed is +60%; at level 60+ with Journeyman Riding (150+), the next mount application gives +100%. Other mounts, bonuses and slows retain native behavior. The spell tooltip can still describe the native fixed epic speed, and TBC/Wrath may show a question-mark item icon for a custom entry. Actual movement is server-controlled. No client patch or addon change is required. The item definition is refreshed on login.

After deployment/restart, startup backfill sends one whistle to existing non-deleted level-40+ player characters. Online level-up and login retry the same grant. Random bot accounts are excluded using the existing utility-grant account list. Lower-level new characters receive it only once they reach 40.

The grant key is **mantech_black_war_raptor_v1** in mantech_character_grants. Grant history, bags/bank/equipped items, pending mail and unsaved online inventory suppress duplicates. Existing ownership without local grant history records an acknowledgement without generating mail. The original item 18246 or learned native spell 22721 is a different mount and does not suppress the custom gift. Existing utility grants are unchanged.

Character-copy tooling must preserve custom item entry **65003** across all three expansions and import inventory/bank before login/grant callbacks. Treat it as a persistent reusable item, like 65000-65002; do not convert it into a learned mount or replace it with 18246. Copy grant history with remapped character GUIDs if supported. A missing local history record is safe once the actual item has been imported; deleting an already-granted gift does not generate a replacement.

Apply sql/custom/world/20260911_01_black_war_raptor_reward.sql with the matching core binary before restart. The migration inserts only the custom item; no native world rows or character schema are modified. Automated tests exercise the real grant and speed handlers, level/riding boundaries, original-mount isolation, and SQL against temporary production-schema copies. Live mail/mount validation follows the user-controlled restart.
