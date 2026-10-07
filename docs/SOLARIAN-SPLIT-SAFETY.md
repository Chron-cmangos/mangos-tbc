# Solarian native split safety

The split callbacks previously indexed 0, 1 and 2 of a vector whose entries are
added only by successful spotlight summons. Failed summons could therefore read
beyond its size. Summons despawned between delayed callbacks could also omit
required adds/teleport without resetting. The delayed callbacks used the default
TIMER_ALWAYS policy, which the native reset-on-evade implementation intentionally
does not cancel.

Validate exactly three distinct live spotlight creatures before either callback.
Invalid sets log one existing-core error and invoke native EnterEvadeMode; no
missing mechanics are bypassed and no substitute summons are created. Both split
callbacks, split creation delay and void transition delay now use the existing
TIMER_COMBAT_COMBAT policy and phase/life/combat guards. Reset clears the old list
and restores normal combat state. A successful split restores the melee state
that split entry disabled. Normal summon counts, spell IDs, delays, phase damage,
rewards and health are unchanged.

`tests/test_solarian_split.py` compiles actual callbacks against controlled map
fixtures: 0/1/2/4 entries, missing/dead/removed/wrong/duplicate portals, despawn
between callbacks, stale callbacks and the valid three-portal path. It reproduces
the pre-fix unchecked empty access with bounds-checking fixture storage. Native
world builds and live phase/wipe tests are separate. No DB migration is needed.
This defect is not attributed to any previously reported production crash.
