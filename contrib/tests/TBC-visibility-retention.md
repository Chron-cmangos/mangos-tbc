> Historical review notes. The integrated release preserves current Arch4 timing and omits the extra telemetry described below. See doc/RETENTION-TRAVEL-RELEASE-20260914.md.

# TBC visibility retention correction

Base: deployed Arch 3 core b9af022a2, with playerbots 407f4cd53 unchanged.
The release branch also merges the previously approved ManTech master movement-height guard (9883cd129).

## Confirmed source defect

Camera::UpdateVisibilityForOwner constructs VisibleNotifier, which copies the player's client GUID set. The visitor calls Player::UpdateVisibilityOf and AddAtClient, including for bots. VisibleNotifier::Notify previously returned for bots before its out-of-range reconciliation. Objects outside subsequently visited cells therefore retained their forward/reverse visibility associations until another lifecycle path removed them. Repeated roaming can grow both the retained set and the cost of copying/scanning it.

The fix moves the bot-only notification return after existing reconciliation, preserving transport passengers, moving transports, overridden visibility, and phase handling. It deliberately does not disable bot cameras, HasAtClient state, perception, or combat behavior. It also removes orphaned forward/reverse GUIDs when the corresponding object/player no longer exists on that map.

The early bot return is inherited from upstream playerbot integration (git blame 62cb97ac64, March 2024), not newly introduced by this patch or Arch 3. Its contribution to the production slowdown requires the controlled before/after run; a source regression test is not a live heap profile.

Map::m_objRemoveList also previously retained every removed creature/gameobject GUID solely for a diagnostic message. It now retains a FIFO history of at most 4096 distinct entries per map. This does not change removal, spawning, respawn, or database data.

## Regression verification

Run in an MSVC developer shell:

```
python contrib/tests/visibility_retention_regression.py --baseline
python contrib/tests/visibility_retention_regression.py
python contrib/tests/movement_height_regression.py
```

The first command requires the old deployed method to fail a repeated-roaming cleanup check. The corrected actual C++ Notify body must pass with playerbots enabled and disabled. Cases cover roaming through 200 sets of 32 objects, reverse links, missing objects, human notification, bots, transports, overridden visibility, phase changes, and 100000 removals with a bounded diagnostic history. The harness uses controlled interfaces, not a full game simulation.

## Production verification and telemetry

- Existing PerformanceLog settings control all new output; no config or DB migration is needed.
- VISIBILITY_SUMMARY: once per map per existing five-minute world summary. Reports human/bot client GUID totals and maxima, plus bounded removal history size. Only reads collection sizes; it does not enumerate the retained GUIDs.
- SLOW_OBJECT_SEND: only sends lasting at least PerformanceLog.SlowMapUpdateMs, rate-limited per map by PerformanceLog.DetailIntervalMs. Splits build, worker wait (included in build), field-packet send, visibility reconciliation, create/aura, remove, and visibility-packet send times. Recipient batches are not unique recipient counts.
- Compare at 4000 bots on the same VM. The original run's average update rose from 19–24 ms to 77–81 ms over several hours; private memory rose approximately 541 MiB in the last 55-minute interval of the pre-fix review.
- A restart alone lowers memory; early lower numbers do not validate the correction. Check visibility totals, memory growth, and update-time trend over a comparable runtime and normal human gameplay.
- Verify bot/human visibility, stealth reveal, party follow, dungeon entry/exit, and a boat/zeppelin trip. The patch does not change transition or transport algorithms, but these exercise retained-visibility exceptions.

No production deployment or sustained post-fix test has occurred at build preparation time. These corrections do not prove that every source of memory growth is fixed.
