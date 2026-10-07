#ifndef MANGOS_PORTABLE_REPAIR_VENDOR_H
#define MANGOS_PORTABLE_REPAIR_VENDOR_H

#include "Common.h"

// Dedicated services for the reusable Portable Repair Hammer. Native
// engineering summons, vendor stock and item definitions remain unchanged.
namespace PortableRepairVendor
{
    constexpr uint32 HAMMER_ITEM = 65001;
    constexpr uint32 CREATURE_ENTRY = 65001;

    inline uint32 ResolveSummonEntry(uint32 itemEntry, uint32 spellId, uint32 nativeEntry)
    {
        if (itemEntry == HAMMER_ITEM &&
            ((spellId == 22700 && nativeEntry == 14337) ||
             (spellId == 44389 && nativeEntry == 24780)))
            return CREATURE_ENTRY;
        return nativeEntry;
    }

    inline uint32 GetBuyPrice(uint32 vendorEntry, uint32 itemEntry, uint32 nativePrice)
    {
        // These gathered reagents cost 30 copper only at the Hammer vendor.
        // Keep the original item IDs so native spell reagent checks still work.
        if (vendorEntry == CREATURE_ENTRY &&
            (itemEntry == 17056 || itemEntry == 17057 || itemEntry == 17058))
            return 30;
        return nativePrice;
    }
}

#endif
