# ManTech baseline module contract

TBC's baseline requires BUILD_MODULES, BUILD_MODULE_DUALSPEC and
BUILD_MODULE_TRAININGDUMMIES and BUILD_MODULE_TRANSMOG. Defaults are established before module discovery;
an old CMake cache disabling a required module fails configuration. Reconfigure
that cache explicitly with all four flags ON. Only deliberate non-baseline
builds should set MANTECH_REQUIRE_BASELINE_MODULES=OFF. Auth-only builds are exempt.

This fixes a release configuration omission: the dual-spec NPC's menu is built
by the module hook, and training-dummy behavior is another module, so vendored
source and enabled runtime configs alone do not preserve either feature.

Release checks must verify required build flags, generated module registration,
compiled feature strings, EXE/PDB identity, and runtime configs/data together.
The dual-spec NPC is 100601; training-dummy entries are 190013/190014/190015.
Keep existing dual-spec tables and character data. Do not rewrite ordinary
gossip SQL to compensate for a missing compiled module.

The dual-spec action save hook now mirrors its active snapshot into the normal
character_action table inside the existing Player::SaveToDB transaction. The old
hook consumed dirty flags before the normal saver, so its claimed mirror did not
actually preserve changed slots. Test from an MSVC developer shell:

    python tests/test_dualspec_action_mirror.py

For a realm verified to have run without the module, inspect current bars before
reactivation. sql/tools/mantech_reactivate_dualspec.sql is an operator-only repair
for the stopped CHARACTER database, not a normal world migration. It reconciles
existing single-spec snapshots and leaves purchased/secondary specs alone. Never
run it speculatively on a healthy module-enabled realm. A receipt prevents repeat
application. Production was not changed as part of the testing-branch fix.

Transmog deployment and exact SQL: see MANTECH_TRANSMOG.md.
