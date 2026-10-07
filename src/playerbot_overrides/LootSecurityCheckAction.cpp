// Realm policy: loot rules do not disable random group or raid members.
// This replaces only the upstream loot security action. Command ownership,
// invitation permissions and native loot distribution remain unchanged.
#include "playerbot/playerbot.h"
#include "playerbot/strategy/actions/SecurityCheckAction.h"

bool ai::SecurityCheckAction::isUseful()
{
    return false;
}

bool ai::SecurityCheckAction::Execute(Event&)
{
    return false;
}
