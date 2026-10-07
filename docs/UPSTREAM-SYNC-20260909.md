# Upstream synchronization — 2026-09-09

CMaNGOS authority: `368b7ef328fa2a472824df55f2195b49f1aaa747`.
Incoming upstream commits: 7.
Playerbots dependency: `70fe52044e3613e52ab1a5bc8ad7346888177c29`.

2b1d4fa37 Fix non-PCH build.
8a0b3a865 Another round of GCC/Clang 'unused parameter' compiler warning fixes.
6037b2972 UpdateData: fix missing member initializer.
d901a09f0 convertEnumToFlag: drop const from the return type.
08cfb99d4 Mark an overridden function with 'override' for consistency.
a9e8a157e world_map_kalimdor: remove unused member.
368b7ef32 Transports: Remove transport from map before delete.

Existing custom safeguards and features are retained, including realm-wide WHO totals, faction filtering, spell-start lifetime protection, portable utilities, and the core loot-policy integration. No archived encounter experiments are restored. The encounter authority manifest now references the reviewed official revision.
