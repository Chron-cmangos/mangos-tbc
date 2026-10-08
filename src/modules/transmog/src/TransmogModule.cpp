#include "TransmogModule.h"
#include "Entities/Creature.h"
#include <algorithm>
#include <cmath>
#include <limits>

#include "Entities/GossipDef.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"

#ifdef ENABLE_PLAYERBOTS
#include "playerbot/PlayerbotAI.h"
#endif

namespace cmangos_module
{
    void SendAddOnMessage(const Player* player, const char* prefix, const char* message)
    {
        if (!player)
            return;

        WorldSession* session = player->GetSession();
        if (!session)
            return;

        WorldPacket data;

        std::ostringstream out;
        if (strstr(prefix, "") != NULL)
        {
            out << prefix << "\t" << message;
        }
        else
        {
            out << message;
        }

        char* buf = mangos_strdup(out.str().c_str());
        char* pos = buf;

        while (char* line = ChatHandler::LineFromMessage(pos))
        {
#if EXPANSION == 0
            ChatHandler::BuildChatPacket(data, CHAT_MSG_ADDON, line, LANG_ADDON);
#else
            ChatHandler::BuildChatPacket(data, CHAT_MSG_WHISPER, line, LANG_ADDON);
#endif
            session->SendPacket(data);
        }

        delete[] buf;
    }

    void SendAddOnMessage(const Player* player, const char* prefix, const std::string& message)
    {
        SendAddOnMessage(player, prefix, message.c_str());
    }

    TransmogModule::TransmogModule()
    : Module("Transmog", new TransmogModuleConfig())
    {

    }

    const cmangos_module::TransmogModuleConfig* TransmogModule::GetConfig() const
    {
        return (TransmogModuleConfig*)Module::GetConfig();
    }

    void TransmogModule::OnInitialize()
    {
	    if (GetConfig()->enabled)
	    {
            // Cleanup non existent characters
            CharacterDatabase.PExecute("DELETE FROM `custom_transmog_active` WHERE NOT EXISTS (SELECT 1 FROM `characters` WHERE `characters`.`guid` = `custom_transmog_active`.`player`);");
            CharacterDatabase.PExecute("DELETE FROM `custom_transmog_discovered` WHERE NOT EXISTS (SELECT 1 FROM `characters` WHERE `characters`.`guid` = `custom_transmog_discovered`.`player`);");
		    
            // Delete corrupted transmog items
		    // CharacterDatabase.Execute("DELETE FROM `custom_transmog_active` WHERE NOT EXISTS (SELECT 1 FROM `item_instance` WHERE `item_instance`.`guid` = `custom_transmog_active`.`item_guid`)");
	    }
    }

    void TransmogModule::OnLoadFromDB(Player* player)
    {
        if (GetConfig()->enabled)
        {
		    if (player)
		    {
#ifdef ENABLE_PLAYERBOTS
                if (sRandomPlayerbotMgr.IsFreeBot(player))
                    return;
#endif

                LoadActiveTransmogs(player);
                LoadDiscoveredTransmogs(player);
		    }
	    }
    }

    void TransmogModule::OnLogOut(Player* player)
    {
	    if (GetConfig()->enabled)
	    {
            if (player)
            {
#ifdef ENABLE_PLAYERBOTS
                if (sRandomPlayerbotMgr.IsFreeBot(player))
                    return;
#endif

			    // Unload transmog config
                const uint32 playerID = player->GetObjectGuid().GetCounter();
                for (auto it = entryMap[playerID].begin(); it != entryMap[playerID].end(); ++it)
                {
                    dataMap.erase(it->first);
                }

                entryMap.erase(playerID);
                playerDiscoveredTransmogs.erase(playerID);
            }
	    }
    }

    void TransmogModule::OnDeleteFromDB(uint32 playerId)
    {
        if (GetConfig()->enabled)
        {
		    CharacterDatabase.PExecute("DELETE FROM `custom_transmog_active` WHERE `player` = %u", playerId);
            CharacterDatabase.PExecute("DELETE FROM `custom_transmog_discovered` WHERE `player` = %u", playerId);

            // Unload transmog config
            for (auto it = entryMap[playerId].begin(); it != entryMap[playerId].end(); ++it)
            {
                dataMap.erase(it->first);
            }

            entryMap.erase(playerId);
            playerDiscoveredTransmogs.erase(playerId);
	    }
    }

    void TransmogModule::OnSetVisibleItemSlot(Player* player, uint8 slot, Item* item)
    {
        if (GetConfig()->enabled)
        {
            if (player && item)
            {
#ifdef ENABLE_PLAYERBOTS
                if (sRandomPlayerbotMgr.IsFreeBot(player))
                    return;
#endif
                // If this is a Druid, and they are in ANY form (Bear, Dire-Bear or Cat etc),
                // we completely block the transmog module from editing ANY visual slots.
                if (player->getClass() == CLASS_DRUID && player->GetShapeshiftForm() != 0)
                {
                    return;
                }

                // Verify the item is actively tracked in our runtime memory layers
                const ObjectGuid itemGUID = item->GetObjectGuid();
                if (dataMap.find(itemGUID) == dataMap.end())
                    return;

                if (uint32 entry = GetTransmogAppearance(item))
                {
                    // Shirt override layer
                    if (slot == EQUIPMENT_SLOT_CHEST)
                    {
                        const ItemPrototype* proto = sObjectMgr.GetItemPrototype(entry);
                        if (proto && proto->SubClass == ITEM_SUBCLASS_ARMOR_MISC) // It's a Shirt appearance
                        {
                            // Push the look onto the Shirt slot channel (EQUIPMENT_SLOT_BODY) instead of Chest
#if EXPANSION == 2
                            player->SetUInt32Value(PLAYER_VISIBLE_ITEM_1_ENTRYID + EQUIPMENT_SLOT_BODY * 2, entry);
#else
                            player->SetUInt32Value(PLAYER_VISIBLE_ITEM_1_0 + EQUIPMENT_SLOT_BODY * MAX_VISIBLE_ITEM_OFFSET, entry);
#endif
                            return;
                        }
                    }

#if EXPANSION == 2
                player->SetUInt32Value(PLAYER_VISIBLE_ITEM_1_ENTRYID + slot * 2, entry);
#else
                player->SetUInt32Value(PLAYER_VISIBLE_ITEM_1_0 + slot * MAX_VISIBLE_ITEM_OFFSET, entry);
#endif
                }
            }
        }
    }

    void TransmogModule::OnStoreItem(Player* player, Item* item)
    {
        if (GetConfig()->enabled)
        {
            if (player && item)
            {
#ifdef ENABLE_PLAYERBOTS
                if (sRandomPlayerbotMgr.IsFreeBot(player))
                    return;
#endif
                // Don't consider items if the player has not finished loading from DB
                if (playerDiscoveredTransmogs.find(player->GetObjectGuid().GetCounter()) != playerDiscoveredTransmogs.end())
                {
                    const uint32 itemEntry = item->GetEntry();
                    if (IsValidTransmog(player, itemEntry))
                    {
                        AddDiscoveredTransmog(player, itemEntry, true, true);
                    }
                }
            }
        }
    }

    void TransmogModule::OnEquipItem(Player* player, Item* item)
    {
        if (GetConfig()->enabled)
        {
            if (player && item)
            {
#ifdef ENABLE_PLAYERBOTS
                if (sRandomPlayerbotMgr.IsFreeBot(player))
                    return;
#endif
                // Don't consider items if the player has not finished loading from DB
                if (playerDiscoveredTransmogs.find(player->GetObjectGuid().GetCounter()) != playerDiscoveredTransmogs.end())
                {
                    const uint32 itemEntry = item->GetEntry();
                    if (IsValidTransmog(player, itemEntry))
                    {
                        AddDiscoveredTransmog(player, itemEntry, true, true);
                    }
                }
            }
        }
    }

    void TransmogModule::OnMoveItemFromInventory(Player* player, Item* item)
    {
        if (GetConfig()->enabled)
        {
            if (player && item)
            {
#ifdef ENABLE_PLAYERBOTS
                if (sRandomPlayerbotMgr.IsFreeBot(player))
                    return;
#endif

			    RemoveTransmog(player, item, false);
		    }
	    }
    }

    std::vector<ModuleChatCommand>* TransmogModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "GetTransmogStatus", std::bind(&TransmogModule::HandleTransmogStatus, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "GetAvailableTransmogs", std::bind(&TransmogModule::HandleGetAvailableTransmogs, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "CalculateTransmogCost", std::bind(&TransmogModule::HandleCalculateTransmogCost, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "ApplyTransmog", std::bind(&TransmogModule::HandleApplyTransmog, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER }
        };

        return &commandTable;
    }

    bool TransmogModule::HandleTransmogStatus(WorldSession* session, const std::string& args)
    {
        if (GetConfig()->enabled)
        {
            Player* player = session->GetPlayer();
            if (player)
            {
                SendActiveTransmogs(player);
                return true;
            }
        }

        return false;
    }

    bool TransmogModule::HandleGetAvailableTransmogs(WorldSession* session, const std::string& args)
    {
        if (GetConfig()->enabled)
        {
            Player* player = session->GetPlayer();
            if (player)
            {
                const uint32 playerID = player->GetObjectGuid().GetCounter();
                
                // If the player's internal runtime tracking map is empty (or missing rows),
                // do a real-time sweep of everything they currently have on or in bags
                // before constructing the UI data block packet.
                if (playerDiscoveredTransmogs[playerID].empty())
                {
                    auto CheckTransmogItem = [&](Item* inventoryItem)
                    {
                        const uint32 itemEntry = inventoryItem->GetEntry();
                        if (IsValidTransmog(player, itemEntry))
                        {
                            AddDiscoveredTransmog(player, itemEntry, false, true);
                        }
                    };

                    helper::ForEachEquippedItem(player, CheckTransmogItem);
                    helper::ForEachInventoryItem(player, CheckTransmogItem);
                    helper::ForEachBankItem(player, CheckTransmogItem);
                }

                // Now push the freshly collected details cleanly down to the client interface
                SendDiscoveredTransmogs(player);
                return true;
            }
        }

        return false;
    }

    bool TransmogModule::HandleCalculateTransmogCost(WorldSession* session, const std::string& args)
    {
        if (GetConfig()->enabled)
        {
            Player* player = session->GetPlayer();
            if (player)
            {
                std::vector<std::pair<uint32, uint32>> slots;
                std::vector<std::string> slotsStr = helper::SplitString(args, ",");
                for (const auto& slotStr : slotsStr)
                {
                    std::vector<std::string> slotPair = helper::SplitString(slotStr, ":");
                    if (slotPair.size() == 2)
                    {
                        if (helper::IsValidNumberString(slotPair[0]) && helper::IsValidNumberString(slotPair[1]))
                        {
                            const uint32 slot = std::stoi(slotPair[0]);
                            const uint32 itemID = std::stoi(slotPair[1]);
                            slots.push_back(std::make_pair(slot, itemID));
                        }
                    }
                }

                SendTransmogCost(player, slots);
                return true;
            }
        }

        return false;
    }

    bool TransmogModule::HandleApplyTransmog(WorldSession* session, const std::string& args)
    {
        if (GetConfig()->enabled)
        {
            Player* player = session->GetPlayer();
            if (player)
            {
                std::vector<std::pair<uint32, uint32>> slots;
                std::vector<std::string> slotsStr = helper::SplitString(args, ",");
                for (const auto& slotStr : slotsStr)
                {
                    std::vector<std::string> slotPair = helper::SplitString(slotStr, ":");
                    if (slotPair.size() == 2)
                    {
                        if (helper::IsValidNumberString(slotPair[0]) && helper::IsValidNumberString(slotPair[1]))
                        {
                            const uint32 slot = std::stoi(slotPair[0]);
                            const uint32 itemID = std::stoi(slotPair[1]);
                            slots.push_back(std::make_pair(slot, itemID));
                        }
                    }
                }

                uint32 cost = 0;
                uint32 tokenID = 0;
                bool succeeded = false;

                if (slots.size() > 0)
                {
                    for (auto& pair : slots)
                    {
                        const uint32 slot = pair.first;
                        const uint32 itemID = pair.second;
                        if (const Item* slotItem = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
                        {
                            std::pair<uint32, uint32> itemCost = CalculateTransmogCost(slotItem->GetEntry());
                            cost += itemCost.first;
                            tokenID = itemCost.second;
                        }
                    }

                    succeeded = tokenID ? player->HasItemCount(tokenID, cost) : player->GetMoney() >= cost;
                }

                if (succeeded)
                {
                    for (auto& pair : slots)
                    {
                        const uint32 slot = pair.first;
                        const uint32 itemID = pair.second;
                        if (Item* slotItem = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
                        {
                            if (itemID > 0)
                            {
                                if (!ApplyTransmog(player, slotItem, itemID, true))
                                {
                                    succeeded = false;
                                    break;
                                }
                            }
                            else
                            {
                                if (!RemoveTransmog(player, slotItem, true))
                                {
                                    succeeded = false;
                                    break;
                                }
                            }
                        }
                    }
                }

                if (succeeded)
                {
                    if (tokenID)
                    {
                        player->DestroyItemCount(tokenID, cost, true);
                    }
                    else
                    {
                        player->ModifyMoney(-(int32)cost);
                    }

                    player->GetPlayerMenu();

                    std::ostringstream out;
                    bool first = true;
                    for (auto& pair : slots)
                    {
                        if (first)
                        {
                            out << pair.first << "," << pair.second;
                            first = false;
                        }
                        else
                        {
                            out << ":" << pair.first << "," << pair.second;
                        }
                    }

                    SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString("ApplyTransmogResult:1:%s", out.str().c_str()));
                }
                else
                {
                    SendAddOnMessage(player, GetChatCommandPrefix(), "ApplyTransmogResult:0");
                }
                
                return true;
            }
        }

        return false;
    }

    void TransmogModule::UpdateItemAppearance(Player* player, Item* item) const
    {
        if (item->IsEquipped())
	    {
            player->SetVisibleItemSlot(item->GetSlot(), item);
	    }
    }

    uint32 TransmogModule::GetTransmogAppearance(const Item* item) const
    {	
        if (item)
        {
            const ObjectGuid itemGUID = item->GetObjectGuid();
            const auto itr = dataMap.find(itemGUID);
            if (itr == dataMap.end()) return 0;
            const auto itr2 = entryMap.find(itr->second);
            if (itr2 == entryMap.end()) return 0;
            const auto itr3 = itr2->second.find(itemGUID);
            if (itr3 == itr2->second.end()) return 0;
            return itr3->second;
        }

        return 0;
    }

    bool TransmogModule::ApplyTransmog(Player* player, Item* item, uint32 transmogItemID, bool updateAppearance)
    {
        if (player && item)
        {
            const ItemPrototype* targetProto = item->GetProto();
            const ItemPrototype* sourceProto = sObjectMgr.GetItemPrototype(transmogItemID);

            if (targetProto && sourceProto)
            {
                bool allowed = false;

                // Base restriction requirement rules
                if (sourceProto->Class == targetProto->Class && 
                    (sourceProto->AllowableClass & player->getClassMask()) != 0 &&
                    (sourceProto->AllowableRace & player->getRaceMask()) != 0)
                {
                    if (targetProto->Class == ITEM_CLASS_ARMOR)
                    {
                        // CPP AUTOMATIC SHIRT APPROVAL
                        if (targetProto->InventoryType == INVTYPE_CHEST && sourceProto->SubClass == ITEM_SUBCLASS_ARMOR_MISC)
                        {
                            allowed = true;
                        }
                        else
                        {
                            // Subclass layer evaluation (e.g. Cloth vs Plate)
                            bool subclassMatch = (sourceProto->SubClass == targetProto->SubClass) || 
                                                 IsSubclassMismatchAllowed(player, sourceProto, targetProto);

                            // Inventory slot layer evaluation (e.g. Chest vs Robe)
                            bool invTypeMatch = (sourceProto->InventoryType == targetProto->InventoryType) || 
                                                IsInvTypeMismatchAllowed(sourceProto, targetProto);

                            allowed = subclassMatch && invTypeMatch;
                        }
                        // Subclass layer evaluation (e.g. Cloth vs Plate)
                        bool subclassMatch = (sourceProto->SubClass == targetProto->SubClass) || 
                                             IsSubclassMismatchAllowed(player, sourceProto, targetProto);

                        // Inventory slot layer evaluation (e.g. Chest vs Robe)
                        bool invTypeMatch = (sourceProto->InventoryType == targetProto->InventoryType) || 
                                            IsInvTypeMismatchAllowed(sourceProto, targetProto);

                        allowed = subclassMatch && invTypeMatch;
                    }
                    else if (targetProto->Class == ITEM_CLASS_WEAPON)
                    {
                        if (IsRangedWeapon(sourceProto->Class, sourceProto->SubClass) != IsRangedWeapon(targetProto->Class, targetProto->SubClass))
                        {
                            allowed = false;
                        }
                        else
                        {
                            bool subclassMatch = (sourceProto->SubClass == targetProto->SubClass) || 
                                                 IsWeaponSubclassMismatchAllowed(player, sourceProto, targetProto);

                            bool invTypeMatch = (sourceProto->InventoryType == targetProto->InventoryType) || 
                                                IsWeaponInvTypeMismatchAllowed(sourceProto, targetProto);

                            allowed = subclassMatch && invTypeMatch;
                        }
                    }
                }

                if (allowed)
                {
                    const ObjectGuid itemGUID = item->GetObjectGuid();
                    const uint32 playerID = player->GetObjectGuid().GetCounter();

                    entryMap[playerID][itemGUID] = transmogItemID;
                    dataMap[itemGUID] = playerID;

                    CharacterDatabase.PExecute("REPLACE INTO `custom_transmog_active` (`item_guid`, `transmog_entry`, `player`) VALUES (%u, %u, %u)", itemGUID.GetCounter(), transmogItemID, playerID);

                    if (updateAppearance)
                    {
                        UpdateItemAppearance(player, item);
                    }

                    return true;
                }
            }
        }

        return false;
    }

    bool TransmogModule::IsSubclassMismatchAllowed(const Player* player, const ItemPrototype* source, const ItemPrototype* target) const
    {
        if (target->Class != ITEM_CLASS_ARMOR)
            return false;

        uint32 sourceSub = source->SubClass;
        uint32 targetSub = target->SubClass;

        // Toggle: Complete mixed armor type freedom (Cloth look on Plate)
        if (GetConfig()->allowMixedArmorTypes)
            return true;

        // Toggle: Downward proficiency ranking (Plate wearer can collect/wear Mail/Leather/Cloth look)
        if (GetConfig()->allowLowerTiers && IsTieredArmorSubclass(targetSub) && PlayerCanWearMaxArmorTier(player, sourceSub))
            return true;

        // Misc aesthetic layer protection overrides
        if (sourceSub == ITEM_SUBCLASS_ARMOR_MISC)
            return source->InventoryType == target->InventoryType;

        return false;
    }

    bool TransmogModule::IsInvTypeMismatchAllowed(const ItemPrototype* source, const ItemPrototype* target) const
    {
        if (target->Class != ITEM_CLASS_ARMOR)
            return false;

        uint32 sourceType = source->InventoryType;
        uint32 targetType = target->InventoryType;

        // Toggle: Check if Chest piece vs full Robe visuals can cross-merge over the core chest slot
        if (GetConfig()->allowChestRobeMismatch)
        {
            if (targetType == INVTYPE_CHEST || targetType == INVTYPE_ROBE)
                return sourceType == INVTYPE_CHEST || sourceType == INVTYPE_ROBE;
        }

        return false;
    }

    bool TransmogModule::IsTieredArmorSubclass(uint32 subclass) const
    {
        return subclass == ITEM_SUBCLASS_ARMOR_PLATE  || 
               subclass == ITEM_SUBCLASS_ARMOR_MAIL   || 
               subclass == ITEM_SUBCLASS_ARMOR_LEATHER|| 
               subclass == ITEM_SUBCLASS_ARMOR_CLOTH;
    }

    bool TransmogModule::PlayerCanWearMaxArmorTier(const Player* player, uint32 tier) const
    {
        uint8 pClass = player->getClass();
        
        // - Plate Wearers: Can wear Plate, Mail, Leather, Cloth, Misc
        // - Mail Wearers: Can wear Mail, Leather, Cloth, Misc (Never Plate)
        // - Leather Wearers: Can wear Leather, Cloth, Misc (Never Plate, Mail)
        // - Cloth Wearers: Can wear Cloth, Misc (Never Plate, Mail, Leather)
        switch (tier)
        {
            case ITEM_SUBCLASS_ARMOR_PLATE:
                // Only native Plate classes can use Plate appearances
                return (pClass == CLASS_WARRIOR || pClass == CLASS_PALADIN);

            case ITEM_SUBCLASS_ARMOR_MAIL:
                // Warriors/Paladins can down-rank to Mail. Native Mail users can use Mail.
                return (pClass == CLASS_WARRIOR || pClass == CLASS_PALADIN || 
                        pClass == CLASS_HUNTER  || pClass == CLASS_SHAMAN);

            case ITEM_SUBCLASS_ARMOR_LEATHER:
                // Everyone except pure primary Cloth wearers can down-rank to Leather
                return (pClass != CLASS_PRIEST && pClass != CLASS_MAGE && pClass != CLASS_WARLOCK);

            case ITEM_SUBCLASS_ARMOR_CLOTH:
            case ITEM_SUBCLASS_ARMOR_MISC:
                // Universal baseline appearances: completely legal for every class in the game
                return true; 
        }
        return false;
    }

    bool TransmogModule::RemoveTransmog(Player* player, Item* item, bool updateAppearance)
    {
        if (player && item)
        {
            const ObjectGuid itemGUID = item->GetObjectGuid();
            if (dataMap.find(itemGUID) != dataMap.end())
            {
                if (entryMap.find(dataMap[itemGUID]) != entryMap.end())
                {
                    entryMap[dataMap[itemGUID]].erase(itemGUID);
                }

                dataMap.erase(itemGUID);
            }

            CharacterDatabase.PExecute("DELETE FROM `custom_transmog_active` WHERE `item_guid` = %u", itemGUID.GetCounter());

            if (updateAppearance)
            {
                UpdateItemAppearance(player, item);
            }

            return true;
        }

        return false;
    }

    bool TransmogModule::IsItemTransmogrified(const Item* item) const
    {
        return GetTransmogAppearance(item) != 0;
    }

    std::vector<std::pair<Item*, uint32>> TransmogModule::GetTransmogrifiedItems(const Player* player, bool equipped) const
    {
        std::vector<std::pair<Item*, uint32>> transmogrifiedItems;
        if (player)
        {
            if (equipped)
            {
                for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
                {
                    if (Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
                    {
                        uint32 transmogItemEntry = GetTransmogAppearance(item);
                        if (transmogItemEntry != 0)
                        {
                            transmogrifiedItems.push_back(std::make_pair(item, transmogItemEntry));
                        }
                    }
                }
            }
            else
            {
                auto playerTransmogsIt = entryMap.find(player->GetObjectGuid());
                if (playerTransmogsIt != entryMap.end())
                {
                    const auto& playerTransmogs = playerTransmogsIt->second;
                    for (const auto it : playerTransmogs)
                    {
                        if (Item* item = player->GetItemByGuid(it.first))
                        {
                            transmogrifiedItems.push_back(std::make_pair(item, it.second));
                        }
                    }
                }
            }
        }

        return transmogrifiedItems;
    }

    std::vector<uint8> GetWeaponAvailableForClass(uint8 playerClass)
    {
        std::map<uint8, std::vector<uint8>> weaponPerClass =
        {
            { CLASS_WARRIOR, { ITEM_SUBCLASS_WEAPON_AXE, ITEM_SUBCLASS_WEAPON_AXE2, ITEM_SUBCLASS_WEAPON_BOW, ITEM_SUBCLASS_WEAPON_GUN, ITEM_SUBCLASS_WEAPON_MACE, ITEM_SUBCLASS_WEAPON_MACE2, ITEM_SUBCLASS_WEAPON_POLEARM, ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_SWORD2, ITEM_SUBCLASS_WEAPON_STAFF, ITEM_SUBCLASS_WEAPON_FIST, ITEM_SUBCLASS_WEAPON_DAGGER, ITEM_SUBCLASS_WEAPON_CROSSBOW } },
            { CLASS_PALADIN, { ITEM_SUBCLASS_WEAPON_AXE, ITEM_SUBCLASS_WEAPON_AXE2, ITEM_SUBCLASS_WEAPON_MACE, ITEM_SUBCLASS_WEAPON_MACE2, ITEM_SUBCLASS_WEAPON_POLEARM, ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_SWORD2 } },
            { CLASS_HUNTER, { ITEM_SUBCLASS_WEAPON_AXE, ITEM_SUBCLASS_WEAPON_AXE2, ITEM_SUBCLASS_WEAPON_BOW, ITEM_SUBCLASS_WEAPON_GUN, ITEM_SUBCLASS_WEAPON_POLEARM, ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_SWORD2, ITEM_SUBCLASS_WEAPON_STAFF, ITEM_SUBCLASS_WEAPON_FIST, ITEM_SUBCLASS_WEAPON_DAGGER, ITEM_SUBCLASS_WEAPON_CROSSBOW } },
            { CLASS_ROGUE, { ITEM_SUBCLASS_WEAPON_AXE, ITEM_SUBCLASS_WEAPON_BOW, ITEM_SUBCLASS_WEAPON_GUN, ITEM_SUBCLASS_WEAPON_MACE, ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_FIST, ITEM_SUBCLASS_WEAPON_DAGGER, ITEM_SUBCLASS_WEAPON_CROSSBOW } },
            { CLASS_PRIEST, { ITEM_SUBCLASS_WEAPON_MACE, ITEM_SUBCLASS_WEAPON_STAFF, ITEM_SUBCLASS_WEAPON_DAGGER, ITEM_SUBCLASS_WEAPON_WAND } },
#if EXPANSION == 2
            { CLASS_DEATH_KNIGHT, { ITEM_SUBCLASS_WEAPON_AXE, ITEM_SUBCLASS_WEAPON_AXE2, ITEM_SUBCLASS_WEAPON_MACE, ITEM_SUBCLASS_WEAPON_MACE2, ITEM_SUBCLASS_WEAPON_POLEARM, ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_SWORD2 } },
#endif
            { CLASS_SHAMAN, { ITEM_SUBCLASS_WEAPON_AXE, ITEM_SUBCLASS_WEAPON_AXE2, ITEM_SUBCLASS_WEAPON_MACE, ITEM_SUBCLASS_WEAPON_MACE2, ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_SWORD2, ITEM_SUBCLASS_WEAPON_STAFF, ITEM_SUBCLASS_WEAPON_FIST, ITEM_SUBCLASS_WEAPON_DAGGER } },
            { CLASS_MAGE, { ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_STAFF, ITEM_SUBCLASS_WEAPON_DAGGER, ITEM_SUBCLASS_WEAPON_WAND } },
            { CLASS_WARLOCK, { ITEM_SUBCLASS_WEAPON_SWORD, ITEM_SUBCLASS_WEAPON_STAFF, ITEM_SUBCLASS_WEAPON_DAGGER, ITEM_SUBCLASS_WEAPON_WAND } },
            { CLASS_DRUID, { ITEM_SUBCLASS_WEAPON_MACE, ITEM_SUBCLASS_WEAPON_MACE2, ITEM_SUBCLASS_WEAPON_POLEARM, ITEM_SUBCLASS_WEAPON_STAFF, ITEM_SUBCLASS_WEAPON_FIST, ITEM_SUBCLASS_WEAPON_DAGGER } },
        };

        return weaponPerClass[playerClass];
    }

    std::vector<uint8> GetArmorAvailableForClass(uint8 playerClass)
    {
        std::map<uint8, std::vector<uint8>> armorPerClass =
        {
            { CLASS_WARRIOR, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH, ITEM_SUBCLASS_ARMOR_LEATHER, ITEM_SUBCLASS_ARMOR_MAIL, ITEM_SUBCLASS_ARMOR_PLATE, ITEM_SUBCLASS_ARMOR_SHIELD } },
            { CLASS_PALADIN, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH, ITEM_SUBCLASS_ARMOR_LEATHER, ITEM_SUBCLASS_ARMOR_MAIL, ITEM_SUBCLASS_ARMOR_PLATE, ITEM_SUBCLASS_ARMOR_SHIELD } },
            { CLASS_HUNTER, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH, ITEM_SUBCLASS_ARMOR_LEATHER, ITEM_SUBCLASS_ARMOR_MAIL } },
            { CLASS_ROGUE, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH, ITEM_SUBCLASS_ARMOR_LEATHER } },
            { CLASS_PRIEST, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH } },
#if EXPANSION == 2
            { CLASS_DEATH_KNIGHT, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH, ITEM_SUBCLASS_ARMOR_LEATHER, ITEM_SUBCLASS_ARMOR_MAIL, ITEM_SUBCLASS_ARMOR_PLATE } },
#endif
            { CLASS_SHAMAN, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH, ITEM_SUBCLASS_ARMOR_LEATHER, ITEM_SUBCLASS_ARMOR_MAIL } },
            { CLASS_MAGE, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH } },
            { CLASS_WARLOCK, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH } },
            { CLASS_DRUID, { ITEM_SUBCLASS_ARMOR_MISC, ITEM_SUBCLASS_ARMOR_CLOTH, ITEM_SUBCLASS_ARMOR_LEATHER } },
        };

        return armorPerClass[playerClass];
    }

    bool TransmogModule::IsValidTransmog(const Player* player, const ItemPrototype* itemPrototype) const
    {
        if (player && itemPrototype)
        {
            if (itemPrototype->Class == ITEM_CLASS_WEAPON || itemPrototype->Class == ITEM_CLASS_ARMOR)
            {
                // Class/race requirement check
                if ((itemPrototype->AllowableClass & player->getClassMask()) == 0 ||
                    (itemPrototype->AllowableRace & player->getRaceMask()) == 0)
                {
                    return false;
                }

                // If it is armor, cross-validate using the newly added configuration options
                if (itemPrototype->Class == ITEM_CLASS_ARMOR)
                {
                    // Call the down-ranking logic helper to evaluate if the class is high enough
                    return PlayerCanWearMaxArmorTier(player, itemPrototype->SubClass);
                }

                // Progressive Weapon Discovery Skill Restriction Rule Checks
                if (itemPrototype->Class == ITEM_CLASS_WEAPON)
                {
                    return PlayerHasWeaponSkill(player, itemPrototype->SubClass);
                }
            }
        }

        return false;
    }

    bool TransmogModule::IsValidTransmog(const Player* player, uint32 itemEntry) const
    {
        return IsValidTransmog(player, sObjectMgr.GetItemPrototype(itemEntry));
    }

    void TransmogModule::LoadActiveTransmogs(Player* player)
    {
        const uint32 playerID = player->GetObjectGuid().GetCounter();
        entryMap.erase(playerID);

        auto result = CharacterDatabase.PQuery("SELECT `item_guid`, `transmog_entry` FROM `custom_transmog_active` WHERE `player` = %u", playerID);
        if (result)
        {
            do
            {
                Field* fields = result->Fetch();
                const ObjectGuid itemGUID = ObjectGuid(HIGHGUID_ITEM, (fields[0].GetUInt32()));
                const uint32 transmogEntry = fields[1].GetUInt32();
                if (sObjectMgr.GetItemPrototype(transmogEntry))
                {
                    dataMap[itemGUID] = playerID;
                    entryMap[playerID][itemGUID] = transmogEntry;
                }
                else
                {
                    sLog.outError("Item entry (Entry: %u, player ID: %u) does not exist, ignoring.", transmogEntry, playerID);
                    //CharacterDatabase.PExecute("DELETE FROM `custom_transmog_active` WHERE `transmog_entry` = %u", transmogEntry);
                }
            } 
            while (result->NextRow());

            // Reload the item visuals
            for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
            {
                if (Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
                {
                    UpdateItemAppearance(player, item);
                }
            }
        }
    }

    void TransmogModule::SendActiveTransmogs(const Player* player)
    {
        const auto transmogItems = GetTransmogrifiedItems(player, true);
        if (!transmogItems.empty())
        {
            bool first = true;
            std::ostringstream out;
            for (const auto& pair : transmogItems)
            {
                const uint32 itemSlot = pair.first->GetSlot();
                const uint32 transmogEntry = pair.second;
                if (first)
                {
                    first = false;
                    out << helper::FormatString("%u,%u", itemSlot, transmogEntry);
                }
                else
                {
                    out << helper::FormatString(":%u,%u", itemSlot, transmogEntry);
                }
            }

            SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString("TransmogStatus:%u:%s", transmogItems.size(), out.str().c_str()));
        }
        else
        {
            SendAddOnMessage(player, GetChatCommandPrefix(), "TransmogStatus:0");
        }
    }

    void TransmogModule::LoadDiscoveredTransmogs(const Player* player)
    {
        if (player)
        {
            const uint32 playerID = player->GetObjectGuid().GetCounter();
            auto& discoveredTransmogs = playerDiscoveredTransmogs[playerID];
            discoveredTransmogs.clear();

            auto result = CharacterDatabase.PQuery("SELECT `item_entry` FROM `custom_transmog_discovered` WHERE `player` = %u", playerID);
            if (result)
            {
                do
                {
                    Field* fields = result->Fetch();
                    const uint32 itemEntry = fields[0].GetUInt32();
                    if (IsValidTransmog(player, itemEntry))
                    {
                        AddDiscoveredTransmog(player, itemEntry, false, false);
                    }
                    else
                    {
                        sLog.outError("Item entry (Entry: %u, player ID: %u) does not exist, ignoring.", itemEntry, playerID);
                        //CharacterDatabase.PExecute("DELETE FROM `custom_transmog_discovered` WHERE `item_entry` = %u", itemEntry);
                    }
                } 
                while (result->NextRow());
            }
            else
            {
                // Calculate all available transmog from the items in the inventory
                auto CheckTransmogItem = [&](Item* inventoryItem)
                {
                    const uint32 itemEntry = inventoryItem->GetEntry();
                    if (IsValidTransmog(player, itemEntry))
                    {
                        AddDiscoveredTransmog(player, itemEntry, false, true);
                    }
                };

                helper::ForEachEquippedItem(player, CheckTransmogItem);
                helper::ForEachInventoryItem(player, CheckTransmogItem);
                helper::ForEachBankItem(player, CheckTransmogItem);
            }
        }
    }

    void TransmogModule::AddDiscoveredTransmog(const Player* player, uint32 itemEntry, bool sendToClient, bool addToDB)
    {
        const uint32 playerID = player->GetObjectGuid().GetCounter();
        auto it = playerDiscoveredTransmogs.find(playerID);
        if (it != playerDiscoveredTransmogs.end())
        {
            auto& availableTransmogs = it->second;
            if (const ItemPrototype* proto = sObjectMgr.GetItemPrototype(itemEntry))
            {
                if (availableTransmogs.find(proto->DisplayInfoID) == availableTransmogs.end())
                {
                    TransmogItem transmogItem;
                    transmogItem.itemClass = proto->Class;
                    transmogItem.itemSubclass = proto->SubClass;
                    transmogItem.itemID = proto->ItemId;
                    transmogItem.displayID = proto->DisplayInfoID;

                    if (player->ViableEquipSlots(proto, &transmogItem.slots[0]))
                    {
                        if (addToDB)
                        {
                            CharacterDatabase.PExecute("INSERT INTO `custom_transmog_discovered` (`player`, `item_entry`) VALUES (%u, %u)", playerID, transmogItem.itemID);
                        }

                        availableTransmogs.insert(std::make_pair(transmogItem.displayID, transmogItem));

                        if (sendToClient)
                        {
                            // Send message to client addon when new item has been discovered
                            SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString("NewTransmog:%u", transmogItem.itemID));

                            // We use 'sendToClient' to determine if this is a real-time event.
                            // If the player is just loading from the DB or shape-shifting silently, 
                            // sendToClient is false, so we don't spam the network channel. 
                            // If they explicitly loot or discover something, sendToClient is true, 
                            // and we broadcast the cross-armor/weapon lists immediately.
                            for (uint8 slot : transmogItem.slots)
                            {
                                if (slot != NULL_SLOT)
                                {
                                    // Send the native item class update packet first
                                    SendDiscoveredTransmogs(player, slot, transmogItem.itemClass, transmogItem.itemSubclass);

                                    // LIVE SYNC FOR ARMOR // Needs to be worked on for fully live sync fix without relogging
                                    if (transmogItem.itemClass == ITEM_CLASS_ARMOR)
                                    {
                                        for (uint8 targetSub = 1; targetSub <= 4; ++targetSub)
                                        {
                                            if (targetSub == transmogItem.itemSubclass)
                                                continue;

                                            ItemPrototype dummyTarget;
                                            dummyTarget.Class = ITEM_CLASS_ARMOR;
                                            dummyTarget.SubClass = targetSub;

                                            if (IsSubclassMismatchAllowed(player, proto, &dummyTarget))
                                            {
                                                SendDiscoveredTransmogs(player, slot, ITEM_CLASS_ARMOR, targetSub);
                                            }
                                        }
                                    }

                                    // WEAPONS (Modern/Loose) // Needs to be worked on for fully live sync fix without relogging
                                    if (transmogItem.itemClass == ITEM_CLASS_WEAPON)
                                    {
                                        if (GetConfig()->allowMixedWeaponTypes == 1 || GetConfig()->allowMixedWeaponTypes == 2)
                                        {
                                            for (uint8 weaponSub = 0; weaponSub <= 20; ++weaponSub)
                                            {
                                                if (weaponSub == transmogItem.itemSubclass)
                                                    continue;

                                                ItemPrototype dummyTarget;
                                                dummyTarget.Class = ITEM_CLASS_WEAPON;
                                                dummyTarget.SubClass = weaponSub;
                                                dummyTarget.InventoryType = proto->InventoryType;

                                                if (IsWeaponSubclassMismatchAllowed(player, proto, &dummyTarget))
                                                {
                                                    SendDiscoveredTransmogs(player, slot, ITEM_CLASS_WEAPON, weaponSub);
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    void TransmogModule::SendDiscoveredTransmogs(const Player* player, int8 slot, int8 itemClass, int8 itemSubclass)
    {
        const auto& discoveredTransmogs = playerDiscoveredTransmogs[player->GetObjectGuid().GetCounter()];

        // Sort by item types
        //        slot            item class + item subclass      item id
        std::map <uint8, std::map<uint32, std::vector<uint32>>> discoveredTransmogsFormatted;
        for (const auto& pair : discoveredTransmogs)
        {
            const TransmogItem& transmogItem = pair.second;

            if (itemClass >= 0 && itemClass != transmogItem.itemClass)
                continue;

            // If loose weapon mixing is globally enabled, bypass subclass verification filters entirely
            // so every weapon subclass entry in your character's unlocked ledger can be evaluated.
            bool isLooseWeaponMode = (transmogItem.itemClass == ITEM_CLASS_WEAPON && GetConfig()->allowMixedWeaponTypes == 2);
            
            if (isLooseWeaponMode)
            {
                // Bypass verification block
            }
            else
            {
                if (itemSubclass >= 0 && itemSubclass != transmogItem.itemSubclass)
                    continue;
            }

            uint32 transmogItemClass = transmogItem.itemClass + transmogItem.itemSubclass;
            
            for (uint8 transmogSlot : transmogItem.slots)
            {
                if (slot >= 0 && slot != transmogSlot)
                    continue;

                if (transmogSlot != NULL_SLOT)
                {
                    bool front = false;
                    if (Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, transmogSlot))
                    {
                        front = item->GetEntry() == transmogItem.itemID;
                    }

                    // ADD THIS OVERRIDE FOR THE SHIRT SLOT
                    if (transmogSlot == 3) // 3 is EQUIPMENT_SLOT_BODY (Shirt)
                    {
                        uint32 proxyClassIndex = ITEM_CLASS_ARMOR + transmogItem.itemSubclass;
                        if (front)
                            discoveredTransmogsFormatted[transmogSlot][proxyClassIndex].insert(discoveredTransmogsFormatted[transmogSlot][proxyClassIndex].begin(), transmogItem.itemID);
                        else
                            discoveredTransmogsFormatted[transmogSlot][proxyClassIndex].push_back(transmogItem.itemID);
            
                        continue; // Move to next slot execution loop safely
                    }

                    // Map into its own native weapon/armor lookup grid index row
                    if (front)
                        discoveredTransmogsFormatted[transmogSlot][transmogItemClass].insert(discoveredTransmogsFormatted[transmogSlot][transmogItemClass].begin(), transmogItem.itemID);
                    else
                        discoveredTransmogsFormatted[transmogSlot][transmogItemClass].push_back(transmogItem.itemID);

                    // Clone item visibility entries across corresponding cross-match subclass index tags.
                    // This forces the client UI menus to populate all matching weapon tabs concurrently.
                    if (transmogItem.itemClass == ITEM_CLASS_WEAPON)
                    {
                        bool isLooseMode = (GetConfig()->allowMixedWeaponTypes == 2);
                        bool isModernMode = (GetConfig()->allowMixedWeaponTypes == 1);

                        if (isLooseMode || isModernMode)
                        {
                            for (uint32 weaponSub = 0; weaponSub <= 20; ++weaponSub)
                            {
                                if (weaponSub == transmogItem.itemSubclass)
                                    continue;

                                const ItemPrototype* srcProto = sObjectMgr.GetItemPrototype(transmogItem.itemID);
                                ItemPrototype dummyTarget;
                                dummyTarget.Class = ITEM_CLASS_WEAPON;
                                dummyTarget.SubClass = weaponSub;
                                dummyTarget.InventoryType = itemSubclass >= 0 ? (itemSubclass + 4) : srcProto->InventoryType;

                                // Validates if weapon matching rules allow this combination
                                if (IsWeaponSubclassMismatchAllowed(player, srcProto, &dummyTarget))
                                {
                                    uint32 proxyWeaponIndex = ITEM_CLASS_WEAPON + weaponSub;
                                    if (front)
                                        discoveredTransmogsFormatted[transmogSlot][proxyWeaponIndex].insert(discoveredTransmogsFormatted[transmogSlot][proxyWeaponIndex].begin(), transmogItem.itemID);
                                    else
                                        discoveredTransmogsFormatted[transmogSlot][proxyWeaponIndex].push_back(transmogItem.itemID);
                                }
                            }
                        }
                    }

                    // PROGRESSIVE MIXED ARMOR NETWORK
                    if (transmogItem.itemClass == ITEM_CLASS_ARMOR)
                    {
                        for (uint32 targetSub = 1; targetSub <= 4; ++targetSub)
                        {
                            if (targetSub == transmogItem.itemSubclass)
                                continue;

                            ItemPrototype dummyTarget;
                            dummyTarget.Class = ITEM_CLASS_ARMOR;
                            dummyTarget.SubClass = targetSub;

                            if (IsSubclassMismatchAllowed(player, sObjectMgr.GetItemPrototype(transmogItem.itemID), &dummyTarget))
                            {
                                uint32 proxyClassIndex = ITEM_CLASS_ARMOR + targetSub;
                                if (front)
                                    discoveredTransmogsFormatted[transmogSlot][proxyClassIndex].insert(discoveredTransmogsFormatted[transmogSlot][proxyClassIndex].begin(), transmogItem.itemID);
                                else
                                    discoveredTransmogsFormatted[transmogSlot][proxyClassIndex].push_back(transmogItem.itemID);
                            }
                        }
                    }
                }
            }
        }

        // ... Rest of the SendDiscoveredTransmogs network packet writing logic left exactly as stock ...
        for (auto& itemSlotIt : discoveredTransmogsFormatted)
        {
            const uint8 itemSlot = itemSlotIt.first;
            for (auto& itemClassIt : itemSlotIt.second)
            {
                const uint8 itemClass = itemClassIt.first;
                const std::vector<uint32>& itemIDs = itemClassIt.second;
                const uint32 amount = itemIDs.size();

                SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString("AvailableTransmogs:%u:%u:%u:%s", itemSlot, itemClass, amount, "start"));

                uint32 itemIDCounter = 0;
                constexpr uint32 itemIDLimit = 10;
                bool first = true;
                std::ostringstream out;
                for (uint32 itemID : itemIDs)
                {
                    if (first) { first = false; out << itemID; }
                    else { out << ":" << itemID; }
                    itemIDCounter++;
                    if (itemIDCounter >= itemIDLimit)
                    {
                        SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString("AvailableTransmogs:%u:%u:%u:%s", itemSlot, itemClass, amount, out.str().c_str()));
                        itemIDCounter = 0; first = true; out.str("");
                    }
                }
                if (!out.str().empty())
                    SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString("AvailableTransmogs:%u:%u:%u:%s", itemSlot, itemClass, amount, out.str().c_str()));

                SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString("AvailableTransmogs:%u:%u:%u:%s", itemSlot, itemClass, amount, "end"));
            }
        }
    }

    std::pair<uint32, uint32> TransmogModule::CalculateTransmogCost(uint32 itemEntry) const
    {
        std::pair<uint32, uint32> result = { 0, 0 };
        uint32& cost = result.first;
        uint32& tokenID = result.second;

        if (GetConfig()->tokenRequired)
        {
            tokenID = GetConfig()->tokenEntry;
            cost = GetConfig()->tokenAmount;
        }
        else
        {
            if (const ItemPrototype* proto = sObjectMgr.GetItemPrototype(itemEntry))
            {
                cost = proto->SellPrice ? proto->SellPrice : 100U;
                cost += GetConfig()->costFee;
                cost *= GetConfig()->costMultiplier;
            }
        }

        return result;
    }

    void TransmogModule::SendTransmogCost(const Player* player, const std::vector<std::pair<uint32, uint32>>& slots) const
    {
        if (player)
        {
            uint32 cost = 0;
            uint32 tokenID = 0;
            bool canPurchase = false;

            if (slots.size() > 0)
            {
                for (auto& pair : slots)
                {
                    const uint32 slot = pair.first;
                    const uint32 itemID = pair.second;
                    if (const Item* slotItem = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
                    {
                        std::pair<uint32, uint32> itemCost = CalculateTransmogCost(slotItem->GetEntry());
                        cost += itemCost.first;
                        tokenID = itemCost.second;
                    }
                }

                canPurchase = tokenID ? player->HasItemCount(tokenID, cost) : player->GetMoney() >= cost;
            }

            SendAddOnMessage(player, GetChatCommandPrefix(), helper::FormatString
            (
                "TransmogCost:%u:%u:%u",
                cost,
                tokenID,
                canPurchase ? 1 : 0
            ));
        }
    }

    bool TransmogModule::IsRangedWeapon(uint32 itemClass, uint32 subclass) const
    {
        return itemClass == ITEM_CLASS_WEAPON && (
            subclass == ITEM_SUBCLASS_WEAPON_BOW ||
            subclass == ITEM_SUBCLASS_WEAPON_GUN ||
            subclass == ITEM_SUBCLASS_WEAPON_CROSSBOW);
    }

    bool TransmogModule::IsWeaponSubclassMismatchAllowed(const Player* player, const ItemPrototype* source, const ItemPrototype* target) const
    {
        uint32 sourceSub = source->SubClass;
        uint32 targetSub = target->SubClass;

        if (IsRangedWeapon(source->Class, sourceSub))
            return true; // Ranged weapons can mix with other ranged weapon types freely (Bows/Guns/Crossbows)

        // MIXED_WEAPONS_MODERN: Allows cross-mismatching specifically within standard 1H or 2H melee sets
        if (GetConfig()->allowMixedWeaponTypes == 1) // 1 = Modern
        {
            switch (targetSub)
            {
                // One-Handed Weapon Suite Mapping (Axes = 0, Maces = 4, Swords = 7)
                case ITEM_SUBCLASS_WEAPON_AXE:
                case ITEM_SUBCLASS_WEAPON_MACE:
                case ITEM_SUBCLASS_WEAPON_SWORD:
                    return (sourceSub == ITEM_SUBCLASS_WEAPON_AXE ||
                            sourceSub == ITEM_SUBCLASS_WEAPON_MACE ||
                            sourceSub == ITEM_SUBCLASS_WEAPON_SWORD);

                // Two-Handed Weapon Suite Mapping (Axes2 = 1, Maces2 = 5, Swords2 = 8)
                case ITEM_SUBCLASS_WEAPON_AXE2:
                case ITEM_SUBCLASS_WEAPON_MACE2:
                case ITEM_SUBCLASS_WEAPON_SWORD2:
                    return (sourceSub == ITEM_SUBCLASS_WEAPON_AXE2 ||
                            sourceSub == ITEM_SUBCLASS_WEAPON_MACE2 ||
                            sourceSub == ITEM_SUBCLASS_WEAPON_SWORD2);

                // Staves and Polearms can cross-mix together exclusively under modern rules
                case ITEM_SUBCLASS_WEAPON_STAFF:
                case ITEM_SUBCLASS_WEAPON_POLEARM:
                    return (sourceSub == ITEM_SUBCLASS_WEAPON_STAFF ||
                            sourceSub == ITEM_SUBCLASS_WEAPON_POLEARM);
            }
        }
        else if (GetConfig()->allowMixedWeaponTypes == 2) // 2 = Loose
        {
            return true; // Complete weapon subclass cross-transmog freedom
        }

        if (sourceSub == ITEM_SUBCLASS_WEAPON_MISC)
            return source->InventoryType == target->InventoryType;

        return false;
    }

    bool TransmogModule::IsWeaponInvTypeMismatchAllowed(const ItemPrototype* source, const ItemPrototype* target) const
    {
        uint32 sourceType = source->InventoryType;
        uint32 targetType = target->InventoryType;

        if (IsRangedWeapon(source->Class, source->SubClass))
            return true;

        if (GetConfig()->allowMixedWeaponTypes == 2) // Loose
            return true;

        // Main-hand / Off-hand classification restriction filters
        if (targetType == INVTYPE_WEAPONMAINHAND || targetType == INVTYPE_WEAPONOFFHAND)
        {
            if (sourceType == INVTYPE_WEAPONMAINHAND || sourceType == INVTYPE_WEAPONOFFHAND)
                return GetConfig()->allowMixedWeaponHandedness;
            if (sourceType == INVTYPE_WEAPON)
                return true;
        }
        else if (targetType == INVTYPE_WEAPON)
        {
            return sourceType == INVTYPE_WEAPONMAINHAND || (GetConfig()->allowMixedWeaponHandedness && sourceType == INVTYPE_WEAPONOFFHAND);
        }

        return false;
    }

    bool TransmogModule::PlayerHasWeaponSkill(const Player* player, uint32 subclass) const
    {
        const uint8 pClass = player->getClass();
        const std::vector<uint8> skilledWeapons = GetWeaponAvailableForClass(pClass);

        for (uint8 skilledSub : skilledWeapons)
        {
            if (subclass == skilledSub)
                return true;
        }
        return false;
    }
}
