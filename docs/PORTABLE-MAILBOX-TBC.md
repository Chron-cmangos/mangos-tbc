# TBC portable mailbox and repair hammer

Item 65000 previously cast Remote Mail Terminal (30524), which has a cast time and refers to missing gameobject 181751. The server log confirmed that the spell finished and charged its cooldown without creating the object.

The custom item now uses client-supported instant self-target dummy spell 1206. The item-scoped script creates existing mailbox 142102 at a nearby valid point for five minutes. Its existing persistent 30-minute item cooldown remains independent from repair and auctioneer cooldowns. Missing/wrong mailbox templates are rejected before casting; failed creation refunds the mailbox cooldown and notifies the player. Login refreshes the item's query response so existing items pick up the new carrier.

The repair script changes only custom creature 65001 summoned by custom item 65001 to faction 12 for Alliance or 29 for Horde. Native engineering item casts and creature templates remain unchanged. Vendor inventory, repair services and summon lifetime are preserved.

Apply sql/custom/world/20260912_01_portable_mailbox_and_repair.sql with this core and restart the TBC world. No client or addon changes. Custom-item bag icons remain unchanged. Classic and Wrath binaries/data are not part of this correction.

The faction callback checks `PortableRepairVendor::CREATURE_ENTRY`. The native summon entry (24780) has already been remapped by `PortableRepairVendor::ResolveSummonEntry` before that callback. Regression tests compile this production resolver and pass its result to the actual spell script.
