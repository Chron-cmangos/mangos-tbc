# Arch 4 memory work

This development branch changes shared-core storage, ownership and allocation. It does not change class rotations, healing thresholds, creature aggro rules, dungeon scripts, visibility, populations or simulation cadence. Network overload intentionally closes an over-budget connection instead of allowing unbounded queued output.

## Changes

* Aura type buckets are allocated on first mutation or when a stable public reference is requested. The public aura container remains `std::list`, including its element iterator behavior. Materialized buckets survive until Unit destruction so stored end iterators do not become dangling when a list becomes empty. Non-escaping internal reads of unused types share a const empty list. Publication of materialized buckets is atomic for concurrent readers.
* Ordinary CreatureEventAI holders reference immutable event definitions. Each AI pins its entry and GUID definition generations; timers, targets and enabled/in-progress flags stay per creature. Database reloads do not invalidate existing holders.
* Outgoing socket writes reserve a quota before allocating and posting payload storage. The defaults are 8 MiB per socket and 256 MiB per process, with a minimum 128-byte charge per message to bound small/empty-message overhead. At most one buffer of up to 64 KiB is reused per socket. That free buffer and arbitrary callback capture memory are not part of the payload quota. WorldSocket callbacks no longer retain a second packet copy. Closing during a completion releases queued callbacks and their ownership references.
* An opt-in (`MANTECH_USE_MIMALLOC=ON`) pinned mimalloc v3.5.1 supplies the world executable's global C++ new/delete operators, including aligned/sized forms. The default remains `MANTECH_USE_MIMALLOC=OFF`, using the original allocator while full workload retention comparisons are evaluated. C malloc/free and allocations owned inside external DLLs are unchanged. Mimalloc is MIT licensed and its archive is pinned by commit and SHA-256 in `cmake/Arch4Allocator.cmake`.
* Wrath only: final instance-navigation cleanup erases the owning mesh record as well as queries. Packed tile headers, vertices, polygons and links remain instance-private. Only immutable detail geometry, BV trees and off-mesh connection definitions are shared through per-tile leases. Content comparison separates changed file generations. The original Detour `addTile` API and on-disk format remain supported; the loader uses the added `addTileShared` API. Query workspaces remain per thread and instance. No active geometry is evicted.

## Measurement

The existing performance summary interval also emits:

* `ARCH4_ENTITIES`: initialized players, loaded creatures (including pets), pets separately, items/bags, game objects, corpses, dynamic objects, aura effects and holders. These categories overlap where stated and should not be summed indiscriminately. They include ordinary NPCs, not only active NPCs or bot AI.
* `ARCH4_MEMORY`: requested bytes/count/peak for Unit base storage, materialized aura list objects, update fields, EventAI holders, private navigation tiles, shared navigation tails, and pending-write quota charges. Kind IDs are defined in `MemoryLedger.h`. These are partial subsystem counters, not a complete heap census. List nodes/sentinels, allocator metadata, derived Unit members, free buffer capacity and unrelated systems are not included in those byte totals.
* `ARCH4_ALLOCATOR`: mimalloc committed, reserved, normal allocated and huge allocated bytes. Normal allocations report allocator size-class bytes, not exact requested sizes. They cover mimalloc-managed allocations only. Reserved address space is not physical memory, and allocator committed memory is not the same measure as whole-process private memory.

Existing `MEMORY_SUMMARY` records retain bot AI/cache counts, map/grid counts, query lifetime counts, queued work, working set and process private memory. Measurements are concurrent snapshots rather than atomic global snapshots. Profile transient allocation stacks separately; do not infer that every gap between these counters and process memory is a leak.

## Validation and limits

Enable `MANTECH_BUILD_ARCH4_TESTS=ON`, build the `arch4_*_tests` targets and run CTest. Tests cover aura iteration/lifetime, concurrent quotas, real socket ordering/ownership/close behavior, and EventAI reference lifetime and independent mutable state. Wrath additionally tests shared geometry against private polygon state, concurrent independent queries, malformed packed ranges, and repeated actual manager instance destruction.

Native tests and server startup do not prove every gameplay interaction. Dev comparisons must use the same database snapshot, population, world coverage and comparable uptime. Preserve a control binary and freshly restore local databases between runs. Keep private snapshots and live configurations outside git. Do not claim the aspirational 25% whole-process reduction until comparable measurements establish it. Longer gameplay and 24–48-hour growth testing remain release gates before production deployment.
