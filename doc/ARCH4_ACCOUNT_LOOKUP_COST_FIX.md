# Indexed account membership

Classic's live stack trace enters `IsInRandomAccountList` while `Channel::Say`
synchronously delivers a message to thousands of recipients. The same sender's
account was searched linearly for every recipient. Recorded slow map updates
spent tens to hundreds of milliseconds in the whole chat delivery path; this
lookup is one measured contributor, not the entire path.

The auxiliary hash index provides average constant-time membership lookup. All
four account registration sites in the pinned module update it, including runtime
account creation. The original list retains its order and duplicate entries for
account/character creation and enumeration. A shared mutex protects index reads
against registration; no extra per-bot cache is allocated. Existing list iteration
still relies on its original caller synchronization.

Native tests compare membership with the former linear search across randomized
IDs, duplicate entries, missing IDs and runtime additions, and exercise concurrent
readers during registration. The CMake override checks each original source hash;
the pinned Playerbots checkout remains unchanged.

This changes lookup cost, not chat recipient selection, reply probability, AI
cadence, combat decisions or configuration. It predates Arch4 and does not establish
the cause of the earlier confounded Phase 2 timing comparison. Measure the deployed
whole-realm result separately from the isolated lookup benchmark.
