# Random-bot group loot policy

Random bots continue participating under Free for All, Master Loot and any
native loot threshold, regardless of guild or account ownership. The group
and raid loot-distribution rules themselves are unchanged.

The core replaces only Playerbots' SecurityCheckAction translation unit at
CMake configure time. The fetched Playerbots checkout is never edited. Both
the scheduled usefulness check and direct execution are inactive; other bot
security checks and intentional passive/stay commands are unaffected.

This policy is always enabled when this core builds Playerbots. No database
or configuration changes are required. Restart the world server to load it.
Bots already placed in passive/stay may need their normal combat/follow
strategies restored; the override does not erase intentional player settings.

Upstream updates remain possible. If that action changes, configuration stops
with a review message: inspect the new action, preserve any unrelated checks,
and update the expected normalized source hash in cmake/playerbot_loot_policy.cmake.
The source-count check also rejects missing or duplicate action implementations.
Do not remove those checks merely to make an upstream update compile.
