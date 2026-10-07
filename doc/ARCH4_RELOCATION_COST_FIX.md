# Relocation shuffle cost

Live Wrath stack samples entered `RandomTeleport` -> `WorldPosition::GetNextPoint`
-> `WeightedShuffle` during world-thread maintenance. Local destination lists reach
14,459 entries. The former algorithm constructed a new probability distribution
for each remaining suffix: quadratic work and repeated allocation.

The replacement uses a local Fenwick tree over positive integer weights, reducing
the full weighted permutation to O(n log n). Both WorldPosition overloads retain
their existing distance weights, random seed, and full output list. All destination
filters and teleport checks remain in their original positions. Other shuffles,
including the floating-point RPG-action weights, are unchanged.

Native tests compare the full permutation, paired weights, and generator state
against the pinned implementation for 1,000 seeds and lists up to 14,459 entries.
On this dev machine, an isolated 14,459-entry case took approximately 477 ms before
and 1.1 ms after. This is a function benchmark, not a measured whole-realm gain.
Floating-point boundary rounding and standard-library implementations can produce
different seeded orders; the positive weighted sampling rule is preserved.

This bottleneck predates Arch4. It is not proof of the cause of the Phase2 map-update
difference. Keep live map/worker timing and deployment validation separate.
