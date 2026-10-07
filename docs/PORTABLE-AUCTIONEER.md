# Portable Auctioneer

Item entry **65002** is the same in Classic, TBC and Wrath. Give a test item with `.additem 65002 1` after applying the world migration and restarting the world server.

The reusable item summons creature entry **65002**, Camotron 9000, a stationary robot chicken auctioneer (native OOX/battle chicken display 6909), for 600 seconds. Item and creature entries are separate namespaces; character transfer copies the inventory item entry, never the summoned creature. Existing character-transfer code must create a fresh destination item-instance GUID as usual.

Spell 21342 is the existing client-supported instant self-target dummy carrier. Its script only handles casts from item 65002. The item has a separate 1,800,000 ms cooldown, persists through logout, and follows the existing mailbox/repair-hammer policy of resetting at world-server restart. It requires no Engineering skill. No client patch or addon change is required.

Summon faction is 12 for Alliance and 29 for Horde. Native auction routing and the existing cross-faction auction configuration remain authoritative. The NPC cannot fight or wander; no native auction, boss or Playerbots logic changes.

Apply `sql/custom/world/20260910_01_portable_auctioneer.sql` to the matching world database with the matching core. Verify entries 65002 and the carrier script binding are unused before first application. The migration only inserts those custom entries and binding; it does not overwrite native records. Reapplication leaves existing entries intact.

## Rollout and verification

Player-only distribution is enabled through the existing creation/login/startup grant hooks. Ownership and pending-mail checks prevent duplicate gifts to copied characters. See [Portable utility grants](PORTABLE-UTILITY-GRANTS.md).

Pre-release checks include native builds for all three cores, migration/schema validation, deployed record verification, executable revision and matching symbol checks. These checks do not constitute an in-game auction transaction test.
