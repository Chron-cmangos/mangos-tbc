# Keep the pinned Playerbots source immutable; compile reviewed replacements.
# Hash checks make an upstream update require an explicit review of this fix.
set(_lifecycle_dir "${CMAKE_BINARY_DIR}/playerbot_lifecycle")
file(MAKE_DIRECTORY "${_lifecycle_dir}")
function(mantech_lifecycle_replace variable before after)
  string(FIND "${${variable}}" "${before}" location)
  if(location EQUAL -1)
    message(FATAL_ERROR "Playerbot map-lifecycle replacement no longer matches")
  endif()
  string(REPLACE "${before}" "${after}" result "${${variable}}")
  set(${variable} "${result}" PARENT_SCOPE)
endfunction()

file(READ "${playerbots_SOURCE_DIR}/playerbot/strategy/Engine.cpp" _lifecycle_text)
string(REPLACE "\r\n" "\n" _lifecycle_text "${_lifecycle_text}")
string(SHA256 _lifecycle_hash "${_lifecycle_text}")
if(NOT _lifecycle_hash STREQUAL "785c1261b10e262a92006ca9d720c02ee082a9c328f31db120cfca0b7dcf06ec")
  message(FATAL_ERROR "Review map-lifecycle fix: upstream Engine.cpp changed")
endif()
mantech_lifecycle_replace(_lifecycle_text [==[bool Engine::DoNextAction(Unit* unit, int depth, bool minimal, bool isStunned)
{]==] [==[bool Engine::DoNextAction(Unit* unit, int depth, bool minimal, bool isStunned)
{
    if (!ai->GetBot()->IsInWorld() || ai->GetBot()->IsBeingTeleported())
        return false;]==])
mantech_lifecycle_replace(_lifecycle_text [==[void Engine::ClearFailures(Action* action, const Event& event)
{]==] [==[void Engine::ClearFailures(Action* action, const Event& event)
{
    // Execute can remove the bot from its map. Do not recalculate a target
    // while completing that action; old-map retry state is no longer valid.
    if (!ai->GetBot()->IsInWorld() || ai->GetBot()->IsBeingTeleported())
    {
        ClearActionFailures();
        return;
    }
    if (actionFailures.empty())
        return;]==])
mantech_lifecycle_replace(_lifecycle_text [==[                        pmo4.reset();

#ifdef PLAYERBOT_ELUNA]==] [==[                        pmo4.reset();

                        // A successful movement action can start a teleport and
                        // detach the bot. End this tick before failure-target
                        // lookups, continuers or alternatives touch the old map.
                        if (!ai->GetBot()->IsInWorld() || ai->GetBot()->IsBeingTeleported())
                        {
                            ClearActionFailures();
                            if (collectDiagnostics)
                            {
                                if (actionExecuted) ++diagnosticSample.ok;
                                else ++diagnosticSample.failed;
                            }
                            delete actionNode;
                            break;
                        }

#ifdef PLAYERBOT_ELUNA]==])
file(WRITE "${_lifecycle_dir}/Engine.cpp.in" "${_lifecycle_text}")
configure_file("${_lifecycle_dir}/Engine.cpp.in" "${_lifecycle_dir}/Engine.cpp" COPYONLY)
get_target_property(_lifecycle_sources playerbots SOURCES)
set(_lifecycle_matches ${_lifecycle_sources})
list(FILTER _lifecycle_matches INCLUDE REGEX "(^|/)Engine[.]cpp$")
list(LENGTH _lifecycle_matches _lifecycle_count)
if(NOT _lifecycle_count EQUAL 1)
  message(FATAL_ERROR "Expected exactly one Engine.cpp source")
endif()
list(REMOVE_ITEM _lifecycle_sources ${_lifecycle_matches})
list(APPEND _lifecycle_sources "${_lifecycle_dir}/Engine.cpp")
set_property(TARGET playerbots PROPERTY SOURCES "${_lifecycle_sources}")
set_source_files_properties("${_lifecycle_dir}/Engine.cpp" TARGET_DIRECTORY playerbots PROPERTIES INCLUDE_DIRECTORIES "${playerbots_SOURCE_DIR}/playerbot;${playerbots_SOURCE_DIR}/playerbot/strategy")

file(READ "${playerbots_SOURCE_DIR}/playerbot/PlayerbotAI.cpp" _lifecycle_text)
string(REPLACE "\r\n" "\n" _lifecycle_text "${_lifecycle_text}")
string(SHA256 _lifecycle_hash "${_lifecycle_text}")
if(NOT _lifecycle_hash STREQUAL "59d32cf4fc0c6039f8936bde5378d43bd84d8674a4a40b39090f4d1708b45f2a")
  message(FATAL_ERROR "Review map-lifecycle fix: upstream PlayerbotAI.cpp changed")
endif()
mantech_lifecycle_replace(_lifecycle_text [==[Unit* PlayerbotAI::GetUnit(ObjectGuid guid)
{
    if (!guid)]==] [==[Unit* PlayerbotAI::GetUnit(ObjectGuid guid)
{
    // GetMap asserts when the bot is detached during a map transfer.
    if (!guid || !bot || !bot->IsInWorld() || bot->IsBeingTeleported())]==])
mantech_lifecycle_replace(_lifecycle_text [==[Creature* PlayerbotAI::GetCreature(ObjectGuid guid) const
{
    if (!guid)]==] [==[Creature* PlayerbotAI::GetCreature(ObjectGuid guid) const
{
    // GetMap asserts when the bot is detached during a map transfer.
    if (!guid || !bot || !bot->IsInWorld() || bot->IsBeingTeleported())]==])
mantech_lifecycle_replace(_lifecycle_text [==[Creature* PlayerbotAI::GetAnyTypeCreature(ObjectGuid guid) const
{
    if (!guid)]==] [==[Creature* PlayerbotAI::GetAnyTypeCreature(ObjectGuid guid) const
{
    // GetMap asserts when the bot is detached during a map transfer.
    if (!guid || !bot || !bot->IsInWorld() || bot->IsBeingTeleported())]==])
mantech_lifecycle_replace(_lifecycle_text [==[GameObject* PlayerbotAI::GetGameObject(ObjectGuid guid)
{
    if (!guid)]==] [==[GameObject* PlayerbotAI::GetGameObject(ObjectGuid guid)
{
    // GetMap asserts when the bot is detached during a map transfer.
    if (!guid || !bot || !bot->IsInWorld() || bot->IsBeingTeleported())]==])
mantech_lifecycle_replace(_lifecycle_text [==[WorldObject* PlayerbotAI::GetWorldObject(ObjectGuid guid)
{
    if (!guid)]==] [==[WorldObject* PlayerbotAI::GetWorldObject(ObjectGuid guid)
{
    // GetMap asserts when the bot is detached during a map transfer.
    if (!guid || !bot || !bot->IsInWorld() || bot->IsBeingTeleported())]==])
# Do not hold one bot's queue mutex while delivering to other bots.
mantech_lifecycle_replace(_lifecycle_text [==[    std::list<ChatQueuedReply> delayedResponses;
    {
        std::scoped_lock lock(chatRepliesMutex);
        while (!chatReplies.empty())
        {
            ChatQueuedReply holder = chatReplies.front();
            time_t checkTime = holder.m_time;
            if (checkTime && time(0) < checkTime)
            {
                delayedResponses.push_back(holder);
                chatReplies.pop();
                continue;
            }
            ChatReplyAction::ChatReplyDo(bot, holder.m_type, holder.m_guid1, holder.m_guid2, holder.m_msg, holder.m_chanName, holder.m_name);
            chatReplies.pop();
        }

        for (std::list<ChatQueuedReply>::iterator i = delayedResponses.begin(); i != delayedResponses.end(); ++i)
        {
            chatReplies.push(*i);
        }
    }
]==] [==[    std::vector<ChatQueuedReply> readyResponses;
    {
        std::scoped_lock lock(chatRepliesMutex);
        // Drain only the current batch. Never hold a bot's reply mutex while
        // broadcasting: delivery may enqueue a reply on another updating bot.
        for (std::size_t remaining = chatReplies.size(); remaining; --remaining)
        {
            ChatQueuedReply holder = std::move(chatReplies.front());
            chatReplies.pop();
            if (holder.m_time && time(0) < holder.m_time)
                chatReplies.push(std::move(holder));
            else
                readyResponses.push_back(std::move(holder));
        }
    }
    for (auto const& holder : readyResponses)
        ChatReplyAction::ChatReplyDo(bot, holder.m_type, holder.m_guid1, holder.m_guid2, holder.m_msg, holder.m_chanName, holder.m_name);
]==])
file(WRITE "${_lifecycle_dir}/chat_queue_block.inc" [==[    std::vector<ChatQueuedReply> readyResponses;
    {
        std::scoped_lock lock(chatRepliesMutex);
        // Drain only the current batch. Never hold a bot's reply mutex while
        // broadcasting: delivery may enqueue a reply on another updating bot.
        for (std::size_t remaining = chatReplies.size(); remaining; --remaining)
        {
            ChatQueuedReply holder = std::move(chatReplies.front());
            chatReplies.pop();
            if (holder.m_time && time(0) < holder.m_time)
                chatReplies.push(std::move(holder));
            else
                readyResponses.push_back(std::move(holder));
        }
    }
    for (auto const& holder : readyResponses)
        ChatReplyAction::ChatReplyDo(bot, holder.m_type, holder.m_guid1, holder.m_guid2, holder.m_msg, holder.m_chanName, holder.m_name);
]==])
file(WRITE "${_lifecycle_dir}/PlayerbotAI.cpp.in" "${_lifecycle_text}")
configure_file("${_lifecycle_dir}/PlayerbotAI.cpp.in" "${_lifecycle_dir}/PlayerbotAI.cpp" COPYONLY)
get_target_property(_lifecycle_sources playerbots SOURCES)
set(_lifecycle_matches ${_lifecycle_sources})
list(FILTER _lifecycle_matches INCLUDE REGEX "(^|/)PlayerbotAI[.]cpp$")
list(LENGTH _lifecycle_matches _lifecycle_count)
if(NOT _lifecycle_count EQUAL 1)
  message(FATAL_ERROR "Expected exactly one PlayerbotAI.cpp source")
endif()
list(REMOVE_ITEM _lifecycle_sources ${_lifecycle_matches})
list(APPEND _lifecycle_sources "${_lifecycle_dir}/PlayerbotAI.cpp")
set_property(TARGET playerbots PROPERTY SOURCES "${_lifecycle_sources}")
set_source_files_properties("${_lifecycle_dir}/PlayerbotAI.cpp" TARGET_DIRECTORY playerbots PROPERTIES INCLUDE_DIRECTORIES "${playerbots_SOURCE_DIR}/playerbot;${playerbots_SOURCE_DIR}/playerbot/strategy")
