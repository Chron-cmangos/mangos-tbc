# Spell startup lifetime correction

SpellStart transfers ownership to SpellEvent before running cast checks and preparation. Caster cleanup can synchronously abort and remove that event while SpellStart continues using its raw `this` pointer. Preparation can also cancel a spell before the immediate cast call. Preserve a temporary strong reference for the duration of SpellStart, stop after cancelled admission, and reject entry to cast for an already finished spell.

The fix is shared by Classic, TBC, and Wrath. It changes ownership and cancelled-cast admission, not spell effects, damage, cooldowns, talents, or encounter mechanics. Playerbot source and database/configuration content do not change.

Evidence: the Classic dump from 2026-09-09 12:45:37 UTC faults in Spell::CheckCast's prefilled target-list traversal. The verified stack reaches it through a bot pet action and immediate SpellStart/Prepare/cast. The spell ID is 19438; the captured object has a finished state, an aborted event, and an invalid target-list node. This supports investigating lifetime/cancellation. The exact callback or operation that originally invalidated the list is not recoverable from this dump and is not claimed as proven by the regression test.

Validation uses the native SpellStart body, initial cast admission, SpellEvent ownership/destruction, EventProcessor implementation, and UniqueTrackablePtr implementation. Controlled callbacks simulate event removal during admission, preparation, and an executing effect; ordinary casts and rejected admission are also checked. The original source fails because the object is destroyed inside PreCastCheck. The corrected sources pass on all three expansions without leaked spells. This is targeted native-code regression testing, not a live reproduction of the complete production crash or a guarantee that every possible heap-corruption source has been eliminated.

Release includes the previously deployed WHO population feature: realm-wide aggregate population, existing faction/configuration rules for displayed names. No database migration or configuration edit is required for this correction. Restart the world process to load the new executable.
