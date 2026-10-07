# Authoritative dungeon teleport cooldown

Classic, TBC and Wrath accept the proposed format unchanged:

```
.tp v1 cooldown123 cooldown self
PBTPC 1 cooldown123 283 300
```

The private system reply has five space-separated tokens: `PBTPC`, version `1`, the echoed request ID, remaining seconds, and the currently configured duration in seconds. Both numbers are unsigned decimal integers from 0 through 3600. The ID permits 1–64 ASCII letters, digits, underscore and hyphen. The only accepted target is the literal `self`, resolved from the authenticated session's account and character, never a selected character or client-supplied GUID.

Use a fresh request ID. Fetch on login/window open and after observed travel or refusals, respecting one snapshot per ten seconds per account/character plus the existing six-command/two-second aggregate limit. Count down locally between snapshots; do not poll every second. The snapshot and unlock catalog have separate ten-second limits.

Examples exercised by controlled tests:

```
PBTPC 1 first 300 300
PBTPC 1 second 290 300
PBTPC 1 initial 0 300
PBTP 1 fast self denied rate_limit
PBTP 1 off self denied disabled
PBTP 1 invalid self denied arguments
```

Failures use `PBTP 1 <id> self denied <reason>`; unsafe IDs are replaced with `invalid`. Invalid token count, target or ID produces `arguments`. Unsupported protocol versions retain the existing `unsupported version` response. Accept only a reply matching an outstanding request ID and validate numeric bounds. A failure means no fresh snapshot; do not replace it with an invented zero. Filter private protocol lines from normal chat once consumed by the addon.

Remaining is the same `max(0, nextTravel - now)` enforced by the server, in whole monotonic-clock seconds. The server truncates its monotonic clock to integer seconds; no additional rounding is applied to the difference. The countdown changes on those second boundaries, so wall-clock precision is within one second, plus network delivery latency. The addon should use its receive time as the local countdown reference and refresh before presenting a newly authoritative value.

`PlayerTravel.CooldownSeconds` remains unchanged: default 300, clamped to 0–3600. Manual `.tp <destination>` and addon check/go travel start the same cooldown after successful native initiation. Checks, refusals, failed initiation, snapshots and replayed go requests never start or renew it. Changing configuration affects future teleports and the reported configured duration; an existing timer keeps its original expiry. Therefore remaining may exceed the currently configured duration after a configuration reload; validate against the supported cap, not against duration.

Reconnects preserve a running timer in the same server process, including a new Player/Session object for the same account/character. A world-server restart clears the in-memory timers and receipts, as before; the new endpoint reports zero after that reset. No persistent cooldown table or new restart behavior is introduced. First-entry dungeon unlock history remains separately persistent and is shared by characters on the same realm account.

Zero remaining describes only the cooldown. It does not mean the player has discovered a destination or is otherwise eligible to teleport. The snapshot does not perform destination eligibility checks and can be read during combat, death, transfers or GM mode while player travel is enabled. It does not bypass check/go/status, grant discovery, reserve a destination or create a travel transaction. GM `.t` and `.tele` retain rank-1 access and their original location list; only `.tp` is available to rank 0.

No addon files were edited. The existing manual command, PBTP transaction replies and PBTPU unlock catalog remain compatible. The tests exercise the actual command adapter and service using controlled external APIs, including manual/addon initiation, ownership, reconnect/restart state, bounds, one-second ticks, failures, malformed inputs, throttling and unchanged expiry. These are fixture results, not a captured live client session.
