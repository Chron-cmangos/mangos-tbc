# Bot action completion during map transfer

Classic 05e3e54c aborted on 2026-09-13 at 09:13:50 after about 57 minutes. The stack is Engine::DoNextAction -> ClearFailures (inlined) -> GetFailureKey -> ReachTargetAction::GetTarget -> FriendlyUnitWithoutAuraValue -> PlayerbotAI::GetUnit -> GetMap assertion. This proves a target lookup ran after the owner lost its map attachment; the precise movement action and bot identity were not captured.

The shared pinned Playerbots source called target resolution after successful execution, even with an empty retry cache. Movement can detach a bot during Execute. End that engine tick when the owner is outside the world or teleporting, discard old-map failure entries, and defer further decisions until the owner is attached again. Guard GUID lookups before the asserting GetMap accessor. Ordinary attached-player target selection, priorities and spell thresholds remain unchanged.

The core CMake override validates the pinned upstream file hashes and generates patched translation units without modifying the vendor snapshot. All three expansion builds use this correction.

Regression: run tests/arch4/map_lifecycle_regression.py ERA ARCH4_WORK_DIRECTORY from an MSVC developer environment after configuration. It compiles the actual ClearFailures and GetUnit method bodies against a minimal map-lifecycle fixture. The unpatched version must reproduce the detached-map error, and the replacement must pass attached lookup, post-action detachment, near teleport, cache accounting and empty-cache cases. This is an isolated method test, not a full live teleport replay. Existing native Arch4 tests and live startup checks are also required. A restart does not establish long-run crash freedom.
