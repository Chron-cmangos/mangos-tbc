# DEV runtime diagnostics

Build with MANTECH_DEV_DIAGNOSTICS=ON on Windows. It defaults OFF and must stay
OFF for production builds. MANTECH_PROFILE_ALLOCATIONS=ON provides on-demand
allocation capture; Memory.SampleAllocations stays 0, so allocation sampling is
not enabled during ordinary DEV running. These options do not limit realm RAM,
entity populations, map loading, simulation cadence or gameplay caches.

Timing scopes record exact call counts and sampled inclusive durations. Detailed
operations sample every 32 invocations per thread; world/map/worker scopes record
each invocation. Per-thread atomic storage avoids shared hot-path locks. Labels
are evaluated only for sampled invocations. CPU clocks are recorded for major
world/map/worker scopes; small scopes record wall time only. Windows thread CPU
time has coarse resolution and cannot identify every wait reason.

A background observer publishes logs/DevDiagnostics-latest.json and bounded
history every 10 seconds. Fixed histogram buckets report percentile upper bounds.
Counters are cumulative, concurrent observations; viewers use differences for
window rates. Inclusive scopes and parallel workers must not be added together
as world elapsed time. Timeline lanes retain map/instance context across worker
handoffs and include map queue and barrier waits.

Write one command to logs/DevDiagnostics.control:

- capture N: an instrumented-scope timeline lasting 1–30 seconds.
- memory N: sample new C++ allocations for 1–60 seconds, then stop new samples
  and symbolize a retained-allocation snapshot on the observer thread.
- enabled 0 / enabled 1: disable / enable timing instrumentation at runtime.

Timing buffers, label tables and trace rings have fixed capacities; overflow
counts are visible. Overflow drops diagnostic observations, never gameplay work.
Four trace files and eight allocation TSV files are rotated. History uses two
bounded files. The fixed diagnostic capacity is exposed separately in memory
output, including allocation tables. These capacities are NOT a server RAM cap.

Memory output includes process private bytes/working set, committed private,
image and mapped address ranges, reserved address space, entity counts and the
existing partial subsystem ledger. Ledger categories can overlap and are not
subtracted into a misleading "leak" remainder. Growth with growing entity/cache
counts differs from growth with stable counts. Allocation captures exclude
pre-existing allocations, arbitrary malloc calls and external DLL heaps. The
free-side Bloom filter skips definitely untracked pointers; sampled frees remain
tracked after capture ends. Dropped allocations/sites are reported in every TSV.

Instrumented timelines are NOT sampled CPU call stacks. Native Windows CPU stack
tracing is a separate capability; this host currently rejects WPR's profiling
privilege. Do not change machine policy or pretend an ETW capture succeeded.

Native tests cover bucket boundaries/percentiles, counts, concurrent snapshots,
stable fixed capacity, trace overflow, publication, and allocation/free tracking
across a stopped capture. Runtime validation must also measure enabled/disabled
overhead at equal population. Diagnostic data identifies candidates for changes;
it does not itself prove a leak or certify a gameplay rewrite.


## Expanded memory and job diagnostics

DEV only. No population, scheduling, allocator, gameplay or RAM-limit changes.
The 10k test configuration is preserved. Named storage is 2048 records per thread
with metric-aware hashing; label storage is 4096 records. Drops remain explicit.
Independent 512-record per-thread slow rings collect major spans >=100ms and
other observed spans >=2ms continuously. Every snapshot exports the largest 100
major and 100 detailed retained spans completed within 15 seconds. Detailed
operations still sample 1/32 calls; these are not complete CPU stack profiles.
Job enqueue-to-start, job execution and caller task-group waits have separate
metrics with map context and job names. Direct MySQL calls and SQL connection
mutex acquisition are timed without recording queries, credentials or player data.

A memory command now measures supported Windows heaps before capture, at the
end of recording and after 60 seconds of frees. C++ allocation totals are exposed
on every snapshot; full sampled site counters are saved separately, including
sites omitted from the top-stack display. This is a surviving-allocation cohort,
not a complete heap leak detector. Pre-existing allocations and direct library
malloc do not have C++ allocation stacks. HeapSummary includes supported Windows
heaps including CRT/library allocations, but not direct VirtualAlloc. Committed
minus allocated includes reusable storage and metadata, not exact fragmentation.
HeapSummary failures/capacity limits and capture duration are reported. It runs
only on request, not in normal world updates. Exclude capture/symbolization
intervals from timing baselines. The observer excludes its own new allocations
from sampling, and releases its owned DbgHelp symbol session after each export.

Microsoft API reference: https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapsummary
