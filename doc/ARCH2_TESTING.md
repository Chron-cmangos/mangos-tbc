# ManTech Classic Arch2 test build

This branch is an isolated scalability experiment built on the deployed ManTech Classic lineage. It includes Playerbot and AHBot.

## Added architecture controls

- Multiple asynchronous database read workers while all writes and transactions remain on one ordered lane.
- A per-database callback time budget so database bursts cannot consume an unlimited world tick.
- Socketless Playerbot session admission throttling; real client sessions always bypass the bot limit.
- Priority database operation and callback lanes for real-player character enumeration and world entry, preventing bot-holder backlogs from blocking login.
- Bounded movement broadcast backpressure with client-local coalescing and movement-only last-resort eviction.
- Per-map adaptive visibility in addition to the existing global adaptive controller.
- Separate workers for disjoint active-cell discovery and minimal AI updates for inactive bots.
- Per-thread Detour navmesh queries so parallel bot workers never share mutable pathfinding search state.
- Accumulated core-update cadence for inactive bots; combat, battleground, grouped, and real-player-adjacent bots remain fully active.
- Timed continent-partition startup diagnostics.
- Working-set/private-memory and database-queue fields in `WORLD_SUMMARY` performance records.

## Database impact

No world, character, realmd, or logs schema migration is required.

## Test order

1. Start `realmd.exe`, then `mangosd.exe`, and verify all continent partitions report an initialization completion time.
2. Log in while bots are still populating. The real client must reach character selection and enter the world without waiting for the bot-admission queue to empty.
3. Verify movement, combat, looting, grouping, battleground queues, taxis, transports, and cross-partition travel.
4. Group with Playerbots and verify commands, following, combat, loot rolls, and `.bot gear` behavior.
5. Watch `Performance.log` for `WORLD_SUMMARY`, `MAP_ADAPTIVE_LOAD`, `MOVEMENT_QUEUE_OVERLOAD`, `SLOW_DB_CALLBACK`, and `SLOW_MAP` records.
6. Run the target bot population long enough to compare private-memory slope, world-update latency, login time, and crash behavior with the prior build.

## Fast isolation switches

Each new execution phase can be disabled independently without changing the binary:

- `MapUpdate.IdleBotThreads = 0`
- `MapUpdate.CellThreads = 0`
- `Playerbot.IdleCoreUpdateSkip = 1`
- `AdaptiveLoad.PerMap.Enabled = 0`
- `Continents.Instanciate = 0`
- All `*DatabaseWorkerThreads = 1`
- `Login.BotSessionsPerTick = 0`

The existing `mantech-classic` branch and live server files are not modified by this test branch.
