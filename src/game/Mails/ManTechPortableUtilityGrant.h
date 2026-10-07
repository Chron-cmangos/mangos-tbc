/*
 * This file is part of the CMaNGOS Project. See AUTHORS file for Copyright information
 */

#ifndef MANGOS_MANTECH_PORTABLE_UTILITY_GRANT_H
#define MANGOS_MANTECH_PORTABLE_UTILITY_GRANT_H

#include "Entities/ObjectGuid.h"

class Player;

namespace ManTechPortableUtilityGrant
{
    bool GrantToCharacter(ObjectGuid characterGuid, Player* onlinePlayer = nullptr);
    bool GrantLevelRewardToCharacter(ObjectGuid characterGuid, Player* onlinePlayer = nullptr);
    void BackfillExistingCharacters();
}

#endif
