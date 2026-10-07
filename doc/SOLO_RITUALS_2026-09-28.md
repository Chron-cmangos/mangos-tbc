# Single-player non-summoning rituals

The world database migration `Updates/ManTech/20260928_solo_non_summoning_rituals.sql`
sets the following ritual templates to one participant wherever present:

- 178465 Altar of Summoning and 178670 Circle of Calling (no fixed live DB spawns).
- 179944 Meeting Stone Summoning Portal.
- 181622 / 193168 soulwell rituals.
- 186811 / 193062 mage refreshment rituals.
- 187359 Zul'Aman Strange Gong. The normal Harrison Jones introduction still applies.

Warlock player summoning portals 36727/194108 and Doom Portal 177193 retain their
original participant counts and all original fields. Earlier migrations already
made Uldaman's two altars and UBRS's Blackrock Altar single-player.

Changing the participant count alone is insufficient for caster-created rituals:
the caster is registered during creation, but the ordinary use handler rejects
the owner and only checks completion after an assistant clicks. The core now
schedules a configured one-participant owned ritual from its object update once
its living player owner is channeling that ritual's creation spell. Completion
uses the existing native ritual handler, including configured delay, selected
target, completion spell, persistent/nonpersistent behavior and channel cleanup.

The update is deferred until after creation; it does not recursively finish the
creation spell. Eligibility is checked again at completion so an interrupted,
replaced or dead caster's channel does not finish the abandoned ritual. Static
altars still require a player click. Rituals requiring multiple participants do
not enter the new completion path.

## Validation and rollout

Live database rows were backed up, updated, compared field by field and reapplied
to verify idempotence. Only the selected participant counts changed; all warlock
summon rows remained identical. Changes: Classic 3, TBC 6, Wrath 8 templates.

Standalone C++ tests extract the production eligibility and scheduling code and
check static objects, normal multi-user rituals, cancelled/replaced channels,
dead/nonplayer casters, empty participant sets, late helpers, configured delay,
no repeated scheduling, non-ready objects and post-completion state.

All three test executables passed. Full server binaries have NOT been built or
deployed for this change. Build Classic, TBC and Wrath locally, deploy them, then
restart each world server. SQL is already applied on the live world databases;
no additional SQL or client patch is needed there. In-game verification remains:
solo meeting-stone summon with a selected group member, solo soulwell/refreshment
creation, the Zul'Aman gong, and unchanged multi-person warlock summons.
