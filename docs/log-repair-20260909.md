# Runtime log repair — 9 September 2026

## Implemented

- Classic: Blizzard only triggers Improved Blizzard when an appropriate talent override is present. Untalented Blizzard retains its ordinary damage behavior.
- Classic/TBC: Judgement requires an existing, valid triggered spell before consuming a seal or performing its triggered cast. Missing/invalid seals cannot cause spell-zero casts; valid seals and TBC talent/trinket effects retain their existing path.
- Shared Playerbots: guild-based randomization policy reads the leader's account from loaded guild membership instead of a synchronous character DB query for offline leaders. Missing guild/member/account data denies randomization for that pass. Human-guild rank protections remain.
- Shared Playerbots: maintenance stage timing identifies slow idle/placement/guild/randomization/strategy/teleport operations (100 ms threshold). Combat cadence is unchanged. This identifies remaining spikes; no assertion that all DB or host contention is eliminated.
- All cores: EventAI permits disabling ranged mode or selecting native NO_MELEE mode without a main spell. Modes that need a main spell retain the check. This repairs the logged Warp Storm case using the existing native mode implementation; no boss-script or instance-mechanic changes.
- All cores: vendor duplicate diagnostics compare conditions, plus extended cost on TBC/Wrath, rather than just item ID. Alternate-cost/conditional offers are preserved; true matching offers still warn.
- Optional LLM character-card file import defaults to disabled and accepts an empty filename. Inline configured personality prompts, chat and existing stored per-bot personalities remain. Explicit file imports escape character names before SQL lookup. Production configs explicitly disable only the absent optional file import.
- TBC database: remove the 26 exact orphan Cabal EventAI rows referencing nonexistent GUIDs; retain any whose spawn now exists. Remove three unreachable vendor gossip options only while no matching vendor/script/template or incoming menu link exists. No creature spawns or boss data are added/replaced.
- Wrath database: restore missing spell 32432 using the exact CMaNGOS core `sql/base/dbc/cmangos_fixes/Spell.sql` definition. Existing definitions are preserved. No invented spell replacement.

## Validation

`tests/log_repair_regression.py` extracts the actual class-script and guild-policy code and native validation predicates. Invoke with `--classic-core`, `--tbc-core`, `--wotlk-core` checkout paths in a Visual Studio developer shell. It checks invalid/no seals, valid seals, dead targets, untalented/talented Blizzard, guild ranks and missing guild records, ranged-mode prerequisites and different-cost/condition vendors. Full native builds check all integrations. These fixtures do not establish live combat or a measured performance improvement. Deployment hashes and production SQL verification are recorded separately in the release artifact.

## Retained / unresolved findings

- Wintergrasp Victory 56902 references absent spell 58931 even in the native original spell data. No verified CMaNGOS definition or intended replacement was found. Keep the warning and existing behavior; do not invent its effect or disable Wintergrasp rewards.
- Intermittent missing-buddy/null-target events require their exact live state; no blanket script range or target-rule changes.
- Custom items 65000/65001 are valid server-side Mailbox/Hammer items absent from client item DBC lists. Preserve them and their diagnostics.
- Registered-but-unbound optional scripts are not automatically bound to arbitrary creatures/triggers.
- Memory growth does not establish a leak. Retain measurement under equivalent warmed-up populations; no claimed leak cure.
- Malformed incoming packet bursts do not identify bot behavior. Existing validation remains enabled.

All identified issues with a supported correction are included. The points above remain explicitly unverified or intentionally preserved; this release does not claim every observed log line has been eliminated. No upstream PR is created.
