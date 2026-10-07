# Cached lookups and reciprocal chat delivery

The Arch4 module pin removes temporary owned strings from successful cached
context lookups and factory key searches. Stored cache keys remain owned, the
ordering comparator is equivalent, and the existing recursive mutex remains.
The native test checks qualifier values, identity, unsupported probes, deletion,
recreation and concurrent lookup/creation. A 400,000-lookup mixed-key fixture went
from 200,000 temporary allocations to zero; this is not a whole-realm speedup claim.

The reply-drain correction is a checked core override of the pinned module source.
Previously UpdateAIInternal held chatRepliesMutex while broadcasting. Delivery may
call QueueChatResponse on a different bot, whose worker may be broadcasting while
holding its own queue mutex. The exact old drain block deadlocks in a bounded
reciprocal-delivery fixture. The corrected block passes that fixture.

Due replies are moved into a local batch while the queue is locked, then dispatched
after unlocking. Future replies retain their order and strings are moved rather
than repeatedly copied through a temporary list. Arrivals during dispatch wait for
the next update. Reply eligibility, messages, probabilities, bot cadence, combat
and class strategies are unchanged. The tests check due/future ordering and both
simultaneous deliveries. No realm configuration or database schema changes apply.

These are concrete existing cost/locking defects. They do not establish the cause
of the earlier confounded Arch4 Phase 2 comparison. The live dev run retains Phase
1 plus fixes; Phase 2 remains reverted. Classic additionally has CPU/elapsed
diagnostics. Windows CPU microseconds can be quantized; raw cycles and aggregates
must accompany interpretation, and map+idle CPU excludes separate cell workers.
