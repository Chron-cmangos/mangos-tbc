# Arch 4 second increment

The first 10,000-bot run was stopped on request with exit code 0 on all three realms. The completed run, selected executables, PDBs, configs and logs are archived in `soak-history/completed-10k-phase1`. This is an initial benchmark, not a completed long-duration stability gate. Its private-memory trend was still rising.

## Implemented scope

All three cores now allocate additional optional Unit containers on first use: immunity buckets, scripted aura locations, tracked aura targets, override scripts and spell-created creature indexes. Exposed references keep a stable container until Unit destruction. Publication is synchronized; this does not grant new permission for concurrent container mutation.

Path point and smoothing scratch vectors move from each PathFinder into synchronous worker-thread leases. Nested calls use independent storage. Each element type retains at most 64 KiB per worker; oversized buffers release capacity when the call ends. Persistent path results and mutable corridors remain private to each PathFinder. Path algorithms and spell/AI thresholds are unchanged.

Inactive terrain payload is checked at the existing map-worker barrier. Above 64 MiB per map, an earlier pass uses the existing zero-reference cleanup path. Referenced grids are excluded. Eligible collision references unload through that same path. This is not a hard cap on the active world or total collision/nav memory.

The ledger adds terrain arrays, collision-model capacities, navigation-query node pools, optional storage, path scratch and queued/in-flight SQL payload estimates. SQL operations remain charged through execution/destruction. Query results and callback captures are not comprehensively measured; string capacity estimates can include inline storage. Collision counts cover WorldModel-owned payload, not every VMap structure. Ledger categories must not be summed into a claimed full-process heap total.

An optional Windows diagnostic executable can sample C++ new/delete stacks. Build with MANTECH_PROFILE_ALLOCATIONS=ON and enable Memory.SampleAllocations. Default sampling is 1/1024 allocations. Fixed tables and bounded probes report dropped samples. It does not see arbitrary malloc calls, external DLL heaps or non-heap mappings. Symbolization and allocation tracking add overhead; diagnostic runs are not fair CPU or RAM comparisons against regular candidates. Both build and runtime options default off.

## Roadmap interpretation

Together with the first increment, each concrete roadmap stream has an implementation: lifetime correction, optional allocator, Unit compaction, immutable navigation sharing, inactive resource cleanup, shared EventAI definitions, network bounds and scratch reuse. The conditional suggestions for broad arenas, object pools and further string/index compaction still require allocation evidence. They were not concrete designs to implement indiscriminately.

The 25% whole-process reduction target is not established. Combat/class/instance correctness beyond the native tests and short dev runs remains unverified. Both increments are integrated with the later map-transfer, chat-queue, account-lookup and relocation-cost fixes. The optional allocator and allocation profiler remain off in regular release builds. These changes do not require a database schema or content migration.

## Validation record

Builds, native tests and bounded diagnostic run results are recorded in the workspace phase2 build logs and final run manifests. The standalone diagnostic sampler returned to zero live samples after normal, aligned and cross-thread allocations were freed, with no dropped allocations or sites in that fixture.
