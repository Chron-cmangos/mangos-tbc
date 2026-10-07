# TBC portable hammer cache compatibility

The local TBC itemcache.wdb still advertises engineering spell 44389 for item
65001, while the live world database uses carrier 28020 and its registered
portable repair summon script. The user confirmed the Wrath compatibility
change works in game and requested equivalent handling for TBC.

TBC CMSG_USE_ITEM supplies an item spell index, not Wrath's spell ID.
CastItemUseSpell already resolves index 0 to the database's spell 28020. Refresh
the authoritative item query response before casting that carrier so the client
receives its current item spell and cooldown data. Restrict the refresh to the
hammer, index 0, and the expected on-use carrier. Preserve inventory/GUID checks,
target checks, item restrictions and native cooldown validation.

Validation: inspected the TBC packet reader, index selection, and query-response
API; git diff --check. No compiler or live-game test run for this change.

Deployment: rebuild TBC locally, deploy mangosd.exe with matching mangosd.pdb,
then restart TBC. No SQL changes. Test a cached hammer, successful vendor summon,
repeat-use cooldown, and cooldown after relog. Wrath is confirmed working by the
user; TBC's live behavior still needs confirmation.
