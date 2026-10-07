# Thaddius encounter lifecycle correction

2026-09-06; testing branches only. Native encounter scripts, not bot-only rules.

Classic and TBC's boss death handler called `BossAI::Aggro(killer)`, which
sets the encounter to IN_PROGRESS and schedules entrance closure. It now calls
the existing `BossAI::JustDied(killer)` handler, which marks DONE and processes
native completion/doors. Wrath already called JustDied and keeps that behavior.

All three versions' Feugen/Stalagg death-prevention handler called JustDied
merely to emit its death text. Because the adds inherit BossAI and have
TYPE_THADDIUS assigned, that call actually marked the whole encounter DONE
while an add was only feigning death. It now emits the existing per-era native
broadcast text directly, retains fake death, health/flags/motion handling and
the ten-second revival timer, and does not call an encounter-completion hook.
GetOtherAdd also handles a missing instance before looking up its sibling.
No boss health, damage, timings, polarity rules or rewards are weakened.

The shared testing checkout's tests/naxxramas_lifecycle_regression.py compiles
the actual native BossAI death body, boss/add handlers and sibling lookup in
all three versions. It verifies both fake deaths preserve IN_PROGRESS, native
boss death changes DONE and despawns adds, text/timer preservation, and absent
instance/sibling cases. It reproduced both prior state defects from pre-fix
HEAD. Full native builds and in-client add revival/wipe/boss-death/doors still
need separate verification; this is not complete Thaddius bot positioning.
No DB/config changes or new diagnostics are required.

