# Upstream core/database release — 2026-09-25

Integrated all remaining reviewed upstream database commits: Classic through
ec4f5961, TBC through ba4755de, Wrath through ffc1ef70. TBC core includes
4771116b1 (instance save field order), 4267950e3 (Vashj intro), and 75f9ae68e
(Dimensius Consume). Thermaplugg caster/null protection was already present.

## Exact deployment files

Run ONE file from the corresponding database repository:
`Updates/ManTech/20260925_upstream_world.sql`.
The matching convenience copies are classic-world.sql, tbc-world.sql, and
wotlk-world.sql under work/upstream-core-db-20260925 in the Codex workspace.
Do not also import the individual upstream files, full ACID data, or the entire
Mana-Tombs rebuild script. Never run these on a characters or authentication DB.

- classic-world.sql -> Classic WORLD database (mangos_classic in current config).
- tbc-world.sql -> mangos_tbc WORLD database.
- wotlk-world.sql -> mangos_wotlk WORLD database.

Back up the affected world databases before applying. Stop the corresponding
world server, apply its SQL, then start it. Deploy the new TBC executable before
starting TBC: the Dimensius core and SQL changes are a matched update.
This batch requires a TBC rebuild only; the previous playerbot batch still
requires Classic/TBC/Wrath rebuilds if not deployed yet. No client patch needed.
The TBC save correction prevents new swapped difficulty/encounter-mask writes;
it does not attempt to guess or rewrite existing instance-save values.

## Packaging and checks

All three database merges retained our baseline history/customizations. ACID
changes are extracted into targeted row updates. Mana-Tombs only changes group
5570190 and adds its two new entries. Upstream fishing SQL omitted area 25 from
its DELETE set; this was fixed in both its original update and the combined file.

All three combined SQL files passed twice on a private MySQL instance using the
current core table schemas. The fixture included a pre-existing fishing area 25
and checked its resulting skill and Dimensius's three target entries. TBC CMake
configuration passed. No server binaries compiled, no runtime testing performed.

No live database changes applied. Live-table snapshots were unavailable: the
configured Classic DB account lacked access, and automatic approval review
rejected reuse of maintenance credentials. Validation therefore used repository
schemas, not live data. Existing customized rows/spawn IDs need a live comparison
before deployment; SQL success alone does not validate world behavior.
