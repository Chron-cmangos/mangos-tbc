/*
 * This file is part of the CMaNGOS Project. See AUTHORS file for Copyright information
 */

#include "Mails/ManTechPortableUtilityGrant.h"
#include "Mails/Mail.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Item.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"

#ifdef ENABLE_PLAYERBOTS
#include "playerbot/PlayerbotAIConfig.h"
#endif

namespace
{
    bool IsBotAccount(uint32 accountId)
    {
#ifdef ENABLE_PLAYERBOTS
        return sPlayerbotAIConfig.IsInRandomAccountList(accountId);
#else
        return false;
#endif
    }

    bool IsEligibleCharacter(uint32 guid)
    {
        auto result = CharacterDatabase.PQuery("SELECT account FROM characters WHERE guid='%u' AND account<>0 AND deleteDate IS NULL", guid);
        if (!result)
            return false;

        return !IsBotAccount(result->Fetch()[0].GetUInt32());
    }

    bool SendSingleItemGrant(ObjectGuid characterGuid, Player* onlinePlayer, uint32 itemId, char const* grantKey, char const* subject)
    {
        uint32 guid = characterGuid.GetCounter();
        // A transferred character may own the item without any local grant
        // history. Inventory includes equipped bags and bank slots; mail also
        // counts, even before its attachment has been collected.
        // Scalar EXISTS always returns a row. A missing result means the read
        // failed, in which case do not risk issuing a duplicate item.
        auto state = CharacterDatabase.PQuery(
            "SELECT EXISTS (SELECT 1 FROM mantech_character_grants WHERE guid='%u' "
            "AND (grant_key='%s' OR (%u IN (65000,65001) AND grant_key='portable_utilities_v1'))), "
            "EXISTS (SELECT 1 FROM character_inventory ci INNER JOIN item_instance ii ON ii.guid=ci.item "
            "WHERE ci.guid='%u' AND ii.itemEntry='%u'), "
            "EXISTS (SELECT 1 FROM mail_items mi INNER JOIN mail m ON m.id=mi.mail_id "
            "WHERE mi.receiver='%u' AND m.receiver='%u' AND mi.item_template='%u')",
            guid, grantKey, itemId, guid, itemId, guid, guid, itemId);
        if (!state)
        {
            sLog.outError("ManTech portable utility grant: ownership query failed for character %u, item %u; grant deferred", guid, itemId);
            return false;
        }

        Field* fields = state->Fetch();
        if (fields[0].GetUInt32())
            return false;

        bool owned = fields[1].GetUInt32() || fields[2].GetUInt32() ||
            (onlinePlayer && onlinePlayer->HasItemCount(itemId, 1, true));
        if (owned)
        {
            // Record the existing item as this character's one-time grant.
            // mail_id=0 records ownership without creating an empty mail.
            CharacterDatabase.BeginTransaction();
            CharacterDatabase.PExecute("INSERT IGNORE INTO mantech_character_grants (guid, grant_key, mail_id, granted_at) VALUES ('%u', '%s', 0, " _UNIXTIME_ ")", guid, grantKey);
            if (!CharacterDatabase.CommitTransactionDirect())
                sLog.outError("ManTech portable utility grant: could not record existing item %u for character %u", itemId, guid);
            return false;
        }

        Item* item = Item::CreateItem(itemId, 1, onlinePlayer);
        if (!item)
        {
            sLog.outError("ManTech portable utility grant: could not create item %u for character %u", itemId, guid);
            return false;
        }

        // The existing mail path commits the item, mail, attachment and unique
        // grant key together before another login/backfill can grant it again.
        MailDraft draft(subject);
        draft.AddItem(item).SetGrantKey(grantKey).SendMailTo(
            MailReceiver(onlinePlayer, characterGuid),
            MailSender(MAIL_NORMAL, uint32(0), MAIL_STATIONERY_GM),
            MAIL_CHECK_MASK_NONE);
        return true;
    }
}

bool ManTechPortableUtilityGrant::GrantToCharacter(ObjectGuid characterGuid, Player* onlinePlayer)
{
    if (onlinePlayer && onlinePlayer->GetObjectGuid() != characterGuid)
        return false;
    if (!IsEligibleCharacter(characterGuid.GetCounter()))
        return false;

    // Individual grant keys allow a copied character with only some utilities
    // to receive exactly the missing items. Classic mail has one attachment.
    bool granted = false;
    granted |= SendSingleItemGrant(characterGuid, onlinePlayer, 65000, "portable_mailbox_v1",
                                   "ManTech Portable Mailbox - 30 Minute Cooldown");
    granted |= SendSingleItemGrant(characterGuid, onlinePlayer, 65001, "portable_repair_v1",
                                   "ManTech Portable Repair Hammer - 30 Minute Cooldown");
    granted |= SendSingleItemGrant(characterGuid, onlinePlayer, 65002, "portable_auctioneer_v1",
                                   "ManTech Camotron 9000 - Portable Auctioneer");
    granted |= SendSingleItemGrant(characterGuid, onlinePlayer, 65004, "portable_bank_v1",
                                   "ManTech Portable Bank - 30 Minute Cooldown");
    granted |= GrantLevelRewardToCharacter(characterGuid, onlinePlayer);
    return granted;
}

bool ManTechPortableUtilityGrant::GrantLevelRewardToCharacter(ObjectGuid characterGuid, Player* onlinePlayer)
{
    if (onlinePlayer && (onlinePlayer->GetObjectGuid() != characterGuid || onlinePlayer->GetLevel() < 40))
        return false;

    auto result = CharacterDatabase.PQuery("SELECT account, level FROM characters WHERE guid='%u' AND account<>0 AND deleteDate IS NULL", characterGuid.GetCounter());
    if (!result)
        return false;

    Field* fields = result->Fetch();
    // At level-up, the online level is newer than the last character save.
    if (IsBotAccount(fields[0].GetUInt32()) || (!onlinePlayer && fields[1].GetUInt32() < 40))
        return false;

    // This reward is for normal player accounts only, including offline
    // backfill. Read directly so a missing account or failed lookup cannot
    // fall back to SEC_PLAYER and accidentally qualify for the gift.
    auto account = LoginDatabase.PQuery("SELECT gmlevel FROM account WHERE id='%u'", fields[0].GetUInt32());
    if (!account || account->Fetch()[0].GetUInt32() != SEC_PLAYER)
        return false;

    // The custom whistle stays reusable in all eras, including Wrath.
    return SendSingleItemGrant(characterGuid, onlinePlayer, 65003, "mantech_black_war_raptor_v1",
                               "ManTech Level 40 Gift - Black War Raptor");
}

void ManTechPortableUtilityGrant::BackfillExistingCharacters()
{
    auto result = CharacterDatabase.Query(
        "SELECT c.guid, c.account FROM characters c "
        "WHERE c.account<>0 AND c.deleteDate IS NULL AND ("
        "NOT EXISTS (SELECT 1 FROM mantech_character_grants g WHERE g.guid=c.guid AND g.grant_key='portable_auctioneer_v1') "
        "OR NOT EXISTS (SELECT 1 FROM mantech_character_grants g WHERE g.guid=c.guid AND g.grant_key='portable_bank_v1') "
        "OR (NOT EXISTS (SELECT 1 FROM mantech_character_grants g WHERE g.guid=c.guid AND g.grant_key='portable_utilities_v1') "
        "AND (NOT EXISTS (SELECT 1 FROM mantech_character_grants g WHERE g.guid=c.guid AND g.grant_key='portable_mailbox_v1') "
        "OR NOT EXISTS (SELECT 1 FROM mantech_character_grants g WHERE g.guid=c.guid AND g.grant_key='portable_repair_v1')))) "
        "OR (c.account<>0 AND c.deleteDate IS NULL AND c.level>=40 AND NOT EXISTS "
        "(SELECT 1 FROM mantech_character_grants g WHERE g.guid=c.guid AND g.grant_key='mantech_black_war_raptor_v1'))");

    if (!result)
    {
        sLog.outString("ManTech portable utility grants: no pending character rows, or backfill query unavailable.");
        return;
    }

    uint32 grantedCharacters = 0;
    do
    {
        Field* fields = result->Fetch();
        if (IsBotAccount(fields[1].GetUInt32()))
            continue;

        ObjectGuid characterGuid(HIGHGUID_PLAYER, fields[0].GetUInt32());
        if (GrantToCharacter(characterGuid))
            ++grantedCharacters;
    }
    while (result->NextRow());

    sLog.outString("ManTech portable utility grants: mailed %u existing non-bot character(s).", grantedCharacters);
}
