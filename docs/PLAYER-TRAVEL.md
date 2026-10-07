# Player dungeon travel

`.tp <destination>` moves only the requesting player to a fixed, expansion-valid CMaNGOS destination. Examples: `.tp SM`, `.tp Ulda`, `.tp deadmines`. `.tp` lists available destinations. Names and aliases are case-insensitive; no arbitrary coordinates, player targets or GM teleport records are accepted. `.tele` remains a moderator command and `.modify tp` remains unchanged.

## Configuration

The distributed configuration defaults to disabled with a 300-second cooldown. To enable on a realm, set the following in mangosd.conf and restart or reload configuration:

```
PlayerCommands = 1
PlayerTravel.Enabled = 1
PlayerTravel.CooldownSeconds = 300
```

Cooldown is clamped to 0..3600 seconds and charged once after successful initiation. No money is charged. Transactions and cooldowns are kept in memory; a server restart clears them. At most six commands per two-second window, 32 retained transactions per account/character, and 4096 account/character records are accepted. Transaction expiry is 60 seconds; terminal receipts are retained for 300 seconds, with opportunistic bounded cleanup. Client IDs should be unique for each new transaction.

## PBTP v1

Send these as ordinary SAY commands, with a unique request ID shared across the transaction:

```
.tp v1 travel123 check deadmines
.tp v1 travel123 go deadmines
.tp v1 travel123 status deadmines
```

Each produces exactly one private system line for the requester:

```
PBTP 1 travel123 deadmines ready ok
PBTP 1 travel123 deadmines pending transfer
PBTP 1 travel123 deadmines arrived ok
```

These are fixture-verified example replies, not a captured live client session. Machine clients should use canonical keys from PLAYER-TRAVEL-DESTINATIONS.json. Request IDs are 1..64 ASCII letters/digits/underscore/hyphen; keys are 1..48. Invalid tokens are replaced with `invalid` in error replies to prevent chat/control-character injection. States and reasons are lowercase ASCII tokens.

Only `ready` from a check authorizes sending go. A ready reply from status does not start anything. Go revalidates current eligibility. Repeated go never teleports twice; status never teleports. Account ID, character GUID, request ID and exact supplied key identify the transaction. Reusing an ID with another key yields `request_conflict`. Unknown go/status and expired transactions yield `expired`; obtain a new ID and check again. Terminal receipts replay while retained. Arrival receipts are revalidated against current position and instance; moving away, dying or starting another transfer changes the receipt to `denied moved_away`.

`pending transfer` means initiation only. `arrived ok` requires an alive player fully in world, no pending transfer, the approved map and a 3D distance no greater than 20 yards. Once arrival is confirmed, the instance ID must continue to match. Poll no faster than every two seconds for at most 60 seconds. Do not recruit on timeout, cancellation, mismatched IDs/keys, late replies or any state other than confirmed arrival. There is no GM fallback, cancel rollback, return teleport or automatic raid conversion.

Possible denial reasons: undiscovered, storage_unavailable, arguments, rate_limit, busy, expired, request_conflict, invalid_destination, wrong_expansion, unavailable_destination, disabled, transfer_busy, not_player, gm_mode, dead, combat, taxi, transport, arena, battleground, instance, controlled, not_leader, too_low_level, raid_required, instance_combat, instance_full, lockout, entry_requirements, cooldown, transfer_failed, moved_away. Wrath also reports battlefield, battle_in_progress or not_owner for Vault of Archavon. Unsupported versions return `unsupported version`.

## Entry policy and placement

Solo players are allowed; grouped requesters must be leader. Combat, death/ghost, taxi, transport, battleground/arena, existing transfer, loss of control/root and travel from inside a dungeon/raid are refused. GM mode is refused because native entry checks exempt it; ordinary GM `.tele` is unchanged. No human group member or retained bot is moved, resurrected, regeared or otherwise modified by this command. Existing bot summoning and combat gear behavior remain separate.

The accepted scope permits existing CMaNGOS points inside or outside. No new outdoor placement coordinates were designed. Points are copied from the inspected world database's game_tele records or native areatrigger_teleport entry targets. Minimum levels use actual entry requirements and respect the realm's native ignore-level setting. Indoor destinations call the expansion's native entry/lockout validation and pass the matching AreaTrigger into TeleportTo; outdoor approaches leave remaining portal requirements to normal entry. Raid difficulty and size stay controlled by native game rules. Vault of Archavon additionally requires enabled Wintergrasp, faction ownership and no active battle.

Scarlet Monastery wings share an approach; SM means the Graveyard key. Upper Blackrock Spire shares the Blackrock Spire approach. Molten Core uses the Blackrock Depths approach; Blackwing Lair uses Blackrock Spire. Eye of Eternity uses the Nexus approach. Follow normal routes/authorized shortcuts from these points. `.tp naxx` means the original level-60 Naxxramas in Classic/TBC and the level-80 version in Wrath. The old Naxxramas key is rejected in Wrath. RFC and Stockade use native indoor entry targets to avoid landing in opposing capital guards.

All expansion-valid keys have a data-backed destination: 32 Classic, 57 TBC, 80 Wrath. Wrong-expansion keys are recognized and denied. See PLAYER-TRAVEL-COMMANDS.md for full and short syntax and placement notes; PLAYER-TRAVEL-DESTINATIONS.json includes exact source IDs, coordinates, orientation, entry triggers, minimum levels and audit metadata.

## Validation and limits

`python tests/player_travel_regression.py <core-root>` compiles the actual command adapter and transaction service with controlled external APIs. It tests every expansion-valid canonical key and alias, native entry handoff, guards, leadership changes, no movement of a second human, check/go/state changes, duplicate and lost-reply handling, cooldown, expiry, stale arrival, rate limits and bounded storage. Static checks verify command security and world-thread dispatch. Compile each native core separately to verify the real interfaces.

The destination evidence is a database/DBC/collision/terrain review and controlled command-routing test. It does not prove every destination with a real client, native instance state, current spawns or both factions in every difficulty. No live character was teleported during validation. These live entry and arrival checks remain to be exercised after restart. No boss scripts, addon files or existing GM locations are changed. The additive character-history migration is required below.

Recruitment discover continues using inclusive min/max levels; validation also caps each expansion at 60/70/80 even if MaxPlayerLevel is configured higher. No new discover syntax is introduced.

## First-entry unlocks (required)

One character must enter the actual dungeon or raid once to unlock its `.tp` destination for every character on the same account in this realm. This is permanent account history, independent of instance lockouts and dungeon resets. Standing outside the portal or merely selecting/checking a destination does not unlock it. Successful native DungeonMap entry records an alive human visitor while travel is enabled; bots, GM mode and incomplete entry do not qualify. Returning to a map already visited does not issue another database write.

Apply both `sql/custom/characters/20260909_01_player_dungeon_travel.sql` and `sql/custom/characters/20260909_02_account_dungeon_travel.sql` to the realm's CHARACTER database before using this binary. The migrations retain legacy `character_dungeon_travel` and add `account_dungeon_travel`, keyed by account and canonical destination, with the earliest first-visit timestamp. No existing character rows or native instance bindings are modified. Account history is queried only for human visits and travel requests, so this feature does not query every random bot at startup. A first visit uses one bounded insert; the in-memory unlock is published only after the database confirms the write. Query/write failure does not grant an unlock. Reconnect/restart reloads saved history. Deleting one character preserves account discovery; deleting the account removes its realm-local unlock rows.

Existing recorded character visits are migrated into account history. Unrecorded older visits are not inferred from account activity, suggested levels or group/instance bindings. Enter once again to establish the record; an alive character logging back into a dungeon after deployment qualifies. Shared instance maps share unlocks: all four Scarlet Monastery wing keys, Lower/Upper Blackrock Spire, and Dire Maul's three wing keys respectively. Molten Core, Blackwing Lair and Eye of Eternity require visiting their own raid maps even though the travel destination is a shared approach. Original Naxxramas and Wrath Naxxramas have different stored keys.

An unvisited destination returns `PBTP 1 <id> <key> denied undiscovered` during check/go, and the manual command explains that the character must enter first. A denied transaction remains terminal; after discovering the dungeon, start a new check with a fresh ID. Permanent unlock does not remove temporary travel restrictions, level requirements, cooldown or native entry rules. For example, a character currently inside a dungeon may have it unlocked but cannot initiate `.tp` until outside.

### Read-only unlock catalog for the addon

The existing check/go/status reply grammar is unchanged. This additional request returns the expansion's complete lock/unlock snapshot, independent of combat, leadership or current map:

```
.tp v1 catalog123 unlocks all
PBTPU 1 catalog123 begin 32
PBTPU 1 catalog123 ragefire_chasm locked
PBTPU 1 catalog123 deadmines unlocked
...one row for each expansion-valid key...
PBTPU 1 catalog123 end 32
```

Counts are 32 Classic, 57 TBC and 80 Wrath. The prefix `PBTPU` distinguishes the read-only catalog from `PBTP` transaction receipts. Each row is a private system message with exactly five space-separated tokens. A row has the canonical key followed by `locked` or `unlocked`; begin/end have the expected row count. The addon must accept only the requested ID, known keys and a complete matching begin/end count; never treat a partial or failed snapshot as all unlocked. Errors use the normal `PBTP 1 <id> all denied <reason>` form (disabled, rate_limit, storage_unavailable or arguments). At most one catalog per ten seconds per account/character is accepted, in addition to the normal command rate limit. Reusing IDs cannot bypass that limit. The catalog never creates a travel transaction, teleports, changes ownership, grants an unlock or charges teleport cooldown.

Cache the catalog for UI display and refresh after login or entering an instance, respecting the ten-second rate limit. Display Locked: enter this dungeon once until the server reports unlocked. Treat locked/unlocked as discovery history only: always perform fresh check/go/status validation when starting travel. No addon-side claim may grant discovery. The manual `.tp` list also labels destinations locked/unlocked.

Controlled fixtures cover first entry, persistence across fresh Player objects, repeat visits without extra writes, shared account discovery and separate accounts, shared-map wings, Naxxramas version separation, read/write failures, blocked recording states and the complete catalog/rate limit. They do not replace live client entry tests. SQL verification uses an isolated temporary table and does not create fake characters or grant real unlocks.

## Authoritative cooldown snapshot

See [PLAYER-TRAVEL-COOLDOWN.md](PLAYER-TRAVEL-COOLDOWN.md) for `.tp v1 <id> cooldown self`, the private PBTPC reply, limits and precise reconnect/restart behavior. This read-only extension does not alter travel eligibility or the configured cooldown.

## Account discovery migration

See [PLAYER-TRAVEL-ACCOUNT.md](PLAYER-TRAVEL-ACCOUNT.md) for shared unlocks, legacy migration, deletion behavior and addon guidance. Cooldowns remain per character.
