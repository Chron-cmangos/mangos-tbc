# Production log repair batch — September 8, 2026

## Shared Playerbots
- Bound routine manager scans to 512 candidates / 10 ms per pass, preserving the rotating cursor and existing successful-work quota. Individual expensive calls finish before yielding; active bot AI/commands retain their existing update schedule.
- Spread expired-value cleanup over passes (128 candidates / 5 ms) rather than visiting the entire population at once. This reduces burst work; it does not establish or claim to cure a memory leak.
- Report slow action execution and the most expensive ProcessBot call. Stop reporting login-queue backpressure when the population target leaves no admission capacity.
- Require a spawned, in-world mailbox within interaction distance. Reject non-interactable generic gameobjects before sending a use request.

## Shared cores
- Remove owned summoned objects and clear ownership before their owner leaves the world. Preserve independent wild summons.
- Skip value-update serialization and update-packet compression for sessions without a client socket. Keep visibility bookkeeping and after-create gameplay packets.
- Prevent duplicate petition signatures from a single bot while permitting distinct bots on shared accounts. Retain human account eligibility rules.
- Rotate principal logs while running under the existing writer mutex, using the current segment day and configured size. Check every five seconds; size can exceed the threshold between checks. Retain matching archives for the configured retention period. Remove the duplicate script-error log open.
- Add object-update phase timings and slow database operation categories. Distinguish invalid UTF-8 from buffer bounds failures; packet validation remains enforced. Include item/parent-spell context in unknown-spell reports.
- Choose an existing native creature model when all its selection weights are zero.

## World data
- All three: correct area trigger 3146 to its registered Southwind Tower script and mark creature 4293's Shadow Bolt as the ranged action.
- Classic: restore missing creature spawn 23120 from the canonical seed, preserving existing path and group references.
- TBC: reverse the former entry-zero cleanup by restoring 7,885 missing, referenced gameobjects from the canonical seed and committed instance inserts. Keep existing GUIDs and all native pool/event/group rules. Remove the destructive entry-zero deletion from the baseline migration. Correct two death-event parameters and restore the missing Deeprun Tram graveyard link.
- Wrath: correct creature 17304's zero model weight, remove exact vendor/template duplicates only, and mark creature 31403's existing ranged spell as its main attack.

## Configuration and limits
Classic's recurring bot deletion flag was already corrected externally to 0 before installation; preserve that value. Existing realm configurations and LLM settings remain intact. New manager settings have built-in defaults.

The following review observations do not yet identify a safe gameplay correction: missing Wrath spell 32432 / trigger 58931, unassigned optional scripts, other intermittent ranged-mode/gossip warnings, and the origin of zero-spell casts. No guessed spell replacements, blanket script bindings, custom-item deletions or combat-AI slowdowns are included. Added diagnostics make further attribution possible. Memory growth and performance gains require a comparable post-restart measurement; no percentage improvement is claimed.

Paused encounter-audit changes are excluded. Regression fixtures execute production lifecycle, packet, logging and scheduling code; native builds validate integration. Live gameplay validation follows restart.
