# Magtheridon native cube contract repair

2026-09-06; playerbot-behavior-enhancements testing branch only.

The native cube AI exposed SetManticronCubeUser and checked its last user's
Shadow Grasp, but never called the setter anywhere in the source. The GO's
short auto-close therefore released the interaction flag while a channel
could remain active. Record the user only after native CastSpell admits the
channel; reject a user already channeling or exhausted. A wrong/missing GO
AI now fails closed instead of being cast to an incompatible type.

This repairs the existing native interaction, not a bot-only fake channel.
Native cast checks, self-damage, Mind Exhaustion, five-beam Shadow Cage and
Blast Nova interruption remain unchanged. Leaving a channel or losing its
player naturally releases the original GUID-based guard. No new timer,
reservation queue, aura deletion, direct boss interruption or teleport exists.

Run tests/test_magtheridon_cube_use.py with the MSVC compiler environment.
It compiles the actual handler and cube AI against controlled stand-ins,
including busy cubes, two independent cubes, exhaustion, duplicate users,
failed cast admission, disappeared owner, encounter reset/dead boss and
missing/wrong AI. It is not an in-world channel/raid test.

Wrath's local dev spell_script_target also had 30410 -> boss 17257, although
the shared native AuraScript makes its target cast 30166. Both dev databases
have five separate 17376 triggers at the five cubes. TBC already targets
17376; the Wrath DB testing migration 5874_mantech_magtheridon_cube_target.sql
restores that target. Each trigger supplies an independent beam to the boss.
The player's second self-targeted effect, native channel damage and exhaustion
are retained. The old 30166 -> boss target is intentionally unchanged.

The migration was tested twice on a temporary table with preservation checks
before application to local Wrath dev. No production data/characters/backups
were touched. Native bot assignment and cube timing are separate ongoing work;
this repair does not claim complete Magtheridon bot support.
