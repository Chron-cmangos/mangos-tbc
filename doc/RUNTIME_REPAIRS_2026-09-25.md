# Runtime repair batch - 2026-09-25

The long-run audit found a string-ID script guard returning early when its map
registry was absent. The relay therefore skipped its TERMINATE_SCRIPT command
instead of terminating. Empty and absent registries now both report no buddy to
the guard; normal commands still fail when a required buddy is absent. The
diagnostic also identifies a string ID correctly instead of calling it a pool.

Buddy searches now prefer an available NPC target when the original source is a
player. Previously that condition tested the source twice and could never take
the intended branch.

Raid leader, raid warning and battleground leader messages now use the same
binary-safe LANG_ADDON handling as their ordinary group channels. Human messages
retain UTF-8 validation, and raid-leader addon payloads cannot invoke chat commands.
This fixes a confirmed parsing inconsistency; the observed Wrath opcode-149 log
does not record channel/language, so not every rejected packet can be attributed
to it without a packet capture.

The script-buddy CTest extracts the production lookup branch and exercises
absent/empty registries, living/dead targets, range checks, player/NPC origins and
all-target selection using bounded fixtures. Full realm behavior still requires
checking after the user restarts the deployed binaries.
