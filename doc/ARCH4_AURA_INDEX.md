# Paged aura pointer index

The baseline already allocates aura lists lazily, but each Unit still embeds
one atomic pointer per aura type. This follow-up stores pointers in eight-slot
pages and allocates a page only when Stable/Mutable first needs one of its lists.
For 317 types the fixed index shrinks from 2536 to 320 bytes on Windows x64.

Pages and materialized std::list objects survive until their Unit is destroyed.
Existing list nodes, iterators, end iterators and borrowed references retain
their lifetimes. Non-escaping reads of unused types allocate nothing. Page/list
publication is atomic; mutation and destruction retain existing owner rules.
No aura effects, class logic, targeting, timers or network data formats change.

The native tests cover all 317 buckets, last partial page, concurrent publication,
unchanged list/reference/end behavior, comparison with ordinary lists and complete
page/list cleanup. MemoryKind::AuraIndexes is appended to the ledger so existing
numeric category IDs remain stable; it counts page payload separately.

An isolated 100000-object fixture with 16 dispersed populated types used
418893824 bytes with the baseline and 329269248 bytes with paging (21.4% less).
This is fixture private memory, not a whole-realm savings claim. Existing sampled
workloads averaged about 8-21 materialized lists per Unit. Fully populated indexes
have additional page/allocator overhead; the normal sparse workload is the target.
Production remains unchanged while the follow-up is validated with 10000 dev bots.
