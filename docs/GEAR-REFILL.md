# Restore gear-command health and mana refill

The recruitment integration cached successful legacy preparation results for 60 seconds. A repeated `.bot gear` / `.bot equip` request could therefore return success without running equipment stat initialization, skipping its health/mana refill.

Restore health and mana to their current maxima for recognized successful gear requests, including cached legacy repeats. Retain equipment-work caching, ownership checks, alive/out-of-combat/transfer checks and explicit request-ID replay protection. Leave rage, energy and other power pools unchanged. Supply commands, unknown parameters and refused requests do not heal.

This is shared Playerbots logic for Classic, TBC and Wrath. No addon, configuration, SQL or native boss changes are required. The existing coordinator regression suite exercises the change under all three expansion macros, including cached repeats, post-gear maxima, non-mana bots, rejected requests and explicit protocol replays. Full native builds validate integration; live gameplay remains to be checked after restart.
