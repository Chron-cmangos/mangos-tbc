# Account dungeon discovery

Dungeon discovery is now shared by all characters on the same account within each realm. Classic, TBC and Wrath retain separate discovery stores and expansion-specific destination keys. Existing character discoveries are retained and migrated, including soft-deleted characters whose saved account is still known. Deleting an individual character does not remove account unlocks. Native account deletion removes the account's discovery rows for this realm.

The PBTP check/go/status protocol, PBTPU unlock catalog and PBTPC cooldown snapshot have not changed. The unlock catalog now reports the requesting account's discoveries. Request it on login/window open and after a first visit, respecting its existing ten-second limit. Update UI wording from "this character" to "this account" for discovery, and key any shared discovery cache by realm and account. A stale display is not authoritative: always perform a fresh check/go transaction.

Cooldowns and travel transactions remain per account/character pair. An alt benefits from an account discovery but keeps its own cooldown and must still satisfy its own level, group, combat, map and entry restrictions. A discovery does not grant eligibility to travel. GM `.t`/`.tele` remain at their original rank requirement and do not become rank-0 commands.

The additive migration is `sql/custom/characters/20260909_02_account_dungeon_travel.sql`. It creates `account_dungeon_travel`, merges existing visits by account/destination using the earliest timestamp, and retains the legacy character table. Legacy rows remain readable during the upgrade window so visits recorded by an old running binary are not missed. Permanent character deletion carries any remaining legacy visits into the account table before deleting the character in the same native transaction.

Unlock reads refresh a per-Player snapshot from the account table and legacy history. There is no shared mutable cross-thread cache or startup scan for bots. This lets an already-connected alt see a new account unlock at its next catalog/eligibility request. Database failure still fails closed rather than granting eligibility from stale cached data. No addon files are edited in this core release.

## Copy-ready prompt for the addon task

Update the dungeon travel UI in all three ManTechPB addon versions for the deployed account-wide dungeon discovery feature. Change discovery wording from "this character" to "this account". This is discovery shared within one realm account, not a bypass of the current character's travel eligibility.

Keep the existing server request format; do not invent an account-ID parameter or a different command:

```
.tp v1 unlock_123 unlocks all
```

The private system replies still use:

```
PBTPU 1 unlock_123 begin 32
PBTPU 1 unlock_123 deadmines unlocked
PBTPU 1 unlock_123 scarlet_library locked
...one row for every supported destination...
PBTPU 1 unlock_123 end 32
```

The count is 32 on Classic, 57 on TBC and 80 on Wrath. The current character's authenticated server session determines the account. Each `unlocked` row now means any character on that realm account has discovered the destination. The addon does not need the numeric account ID to query this.

Accept only the outstanding request ID, known destination keys and a complete matching begin/end snapshot. Store discovery in account-wide SavedVariables under a realm-specific namespace instead of under the character name/GUID. The normal account-specific SavedVariables boundary can identify the account; do not hardcode or request another player's account ID. Invalidate old character-only discovery caches on addon upgrade and refresh on login/window open and after a dungeon visit. Respect one catalog per ten seconds; do not poll every second. Handle incomplete replies or `PBTP 1 <id> all denied <reason>` as unknown/stale data, not as "everything unlocked."

Keep cooldowns, pending travel transactions and eligibility state character-specific. PBTPC cooldown requests stay `.tp v1 <fresh-id> cooldown self`. Account unlock can display "Unlocked for this account," but current-character travel must still run `.tp v1 <fresh-id> check <canonical-key>`, then the existing go/status flow. A low-level, in-combat, nonleader or otherwise ineligible alt must display the server's refusal accurately. Never grant discovery or teleport eligibility from local cached data alone.

Do not modify GM `.t`/`.tele` commands, cooldown duration, core/database logic or teleport locations in the addon task. This release keeps the existing PBTP/PBTPU/PBTPC wire formats compatible.
