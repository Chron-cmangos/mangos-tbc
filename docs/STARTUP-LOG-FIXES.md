# Startup and log rotation repairs

## Logging

- Restrict the implicit Performance.log default to world-server configurations. The authentication server no longer opens the world's performance log merely because it uses the shared logger.
- Close existing streams before reinitializing the logger. The realmd constructor plus explicit initialization otherwise leaked file handles.
- Register the world-server fallback performance stream for rotation, as with explicitly configured logs.
- Preserve append logging when an external handle blocks rename. Retry the affected file after 60 seconds, allowing other logs to rotate normally.
- Handle an empty LogsDir correctly during runtime archive retention.

The earlier runtime-rotation change exposed the shared-file and initialization problems. These errors do not indicate that cleanup deleted the log directory.

## Object-location startup

- Load vmaps from DataDir/vmaps, matching the native CMaNGOS loader contract. The prior bot helper passed DataDir itself and could repeatedly attempt nonexistent map-tree files. Handle the loader result explicitly.
- Index creature, gameobject and pool event membership once after database loading. Preserve the previous first-match order, signed event IDs and current event-activation checks. No event spawn or encounter mechanics are changed.
- Report object-location progress and separate event-check and terrain-area timings.

The vmap helper and repeated event-list scans predate the latest PvP audit. They are verified defects/costs in the reported startup path; the full wall-clock slowdown cannot be attributed solely to a recent audit commit from the available logs.

## Validation and deployment

Production-body tests cover real Windows sharing violations, continued writes, per-file backoff, recovery, repeated initialization, archive retention, signed event membership, missing entries, duplicates, rebuilding, vmap directory/result handling and spawn filtering.

A local benchmark using exported production spawn/event IDs produced identical membership answers for 113,886 Classic, 181,118 TBC and 258,372 Wrath spawns. Event-list scan times were approximately 0.83/2.78/5.20 seconds; index construction plus lookup took approximately 0.002/0.003/0.004 seconds. These are local lookup timings, not production startup-time measurements.

Deploy matching mangosd.exe/PDB and realmd.exe/PDB. Restart both authentication and world processes to release the old authentication process's log handles. No database migration or configuration change is required; existing append, daily/size rotation and retention settings remain in effect. Production startup timings must be checked after the restart.

## Startup regression correction

The corrected bot vmap path exposed a terrain-area lookup that requested navigation tiles before map navigation data existed. TBC aborted in MMapManager::loadMap during object-location loading. GetAreaInfo now requests only the map grid used for its terrain-height test, matching the existing map-only fallback in GetAreaFlag. Vmap area selection, height filtering, event behavior, and navigation loading for movement remain unchanged. The same correction applies to Classic, TBC and Wrath.

The added regression test executes the actual GetAreaInfo body with navigation deliberately uninitialized and proves the old call fails while the corrected call succeeds. It also checks terrain occlusion and missing area/grid cases. Production startup acceptance must still be verified on restart.
