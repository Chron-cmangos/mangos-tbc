/*
 * This file is part of the CMaNGOS Project. See AUTHORS file for Copyright information
 * This program is free software; you can redistribute it and/or modify it under
 * the terms of the GNU General Public License, version 2 or later.
 */
#ifndef MANGOS_PLAYER_TRAVEL_H
#define MANGOS_PLAYER_TRAVEL_H

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <functional>
#include <map>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace PlayerTravel
{
    struct Destination
    {
        const char* key;
        const char* name;
        const char* aliases;
        unsigned firstExpansion, lastExpansion;
        bool available;
        uint32_t map, instanceMap, entryTrigger;
        float x, y, z, orientation;
    };

    inline bool Token(const std::string& text, size_t maximum)
    {
        if (text.empty() || text.size() > maximum)
            return false;
        for (unsigned char c : text)
            if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                (c >= '0' && c <= '9') || c == '_' || c == '-'))
                return false;
        return true;
    }

    struct Reply
    {
        std::string state, reason;
        std::string Line(const std::string& id, const std::string& key) const
        {
            return "PBTP 1 " + (Token(id, 64) ? id : "invalid") + " " +
                (Token(key, 48) ? key : "invalid") + " " + state + " " + reason;
        }
    };

    struct Position
    {
        bool inWorld = false, transferring = true, alive = false;
        uint32_t map = 0, instance = 0;
        float x = 0, y = 0, z = 0;

        bool At(const Destination& destination) const
        {
            if (!inWorld || transferring || !alive || map != destination.map)
                return false;
            const float dx = x - destination.x, dy = y - destination.y, dz = z - destination.z;
            return dx * dx + dy * dy + dz * dz <= 400.0f;
        }
    };

    // Chat commands execute on the world thread (PROCESS_THREADUNSAFE).
    // Store only values and static destination pointers, never Player/Session pointers.
    class Service
    {
    public:
        using Owner = std::pair<uint32_t, uint32_t>; // Account and character GUID.
        static constexpr size_t MaxOwners = 4096;
        static constexpr size_t MaxReceipts = 32;
        static constexpr unsigned MaxCooldown = 3600;
        static constexpr uint64_t Lifetime = 60, Retention = 300;

        bool AllowRequest(Owner owner, uint64_t now)
        {
            Cleanup(now);
            auto found = clients.find(owner);
            if (found == clients.end())
            {
                if (clients.size() >= MaxOwners)
                    return false;
                found = clients.emplace(owner, Client{}).first;
            }
            Client& client = found->second;
            client.lastSeen = now;
            if (now >= client.rateWindow + 2)
            {
                client.rateWindow = now;
                client.requests = 0;
            }
            return ++client.requests <= 6;
        }

        bool AllowCatalog(Owner owner, uint64_t now)
        {
            auto found = clients.find(owner);
            if (found == clients.end() || now < found->second.nextCatalog)
                return false;
            found->second.nextCatalog = now + 10;
            return true;
        }

        bool AllowCooldownSnapshot(Owner owner, uint64_t now)
        {
            auto found = clients.find(owner);
            if (found == clients.end() || now < found->second.nextCooldownSnapshot)
                return false;
            found->second.nextCooldownSnapshot = now + 10;
            return true;
        }

        unsigned RemainingCooldown(Owner owner, uint64_t now) const
        {
            auto found = clients.find(owner);
            if (found == clients.end() || now >= found->second.nextTravel)
                return 0;
            return static_cast<unsigned>(std::min<uint64_t>(found->second.nextTravel - now, MaxCooldown));
        }

        Reply Process(Owner owner, const std::string& id, const std::string& operation,
            const std::string& key, const Destination* destination, unsigned expansion,
            const Position& position, const std::string& eligibility, unsigned cooldown,
            uint64_t now, const std::function<bool()>& teleport)
        {
            if (!Token(id, 64) || !Token(key, 48))
                return {"denied", "arguments"};
            if (operation != "check" && operation != "go" && operation != "status")
                return {"denied", "arguments"};
            auto ownerIt = clients.find(owner);
            if (ownerIt == clients.end())
                return {"denied", "rate_limit"};
            Client& client = ownerIt->second;
            auto found = client.receipts.find(id);
            if (found != client.receipts.end() && found->second.key != key)
                return {"denied", "request_conflict"};
            if (found == client.receipts.end())
            {
                if (operation != "check")
                    return {"denied", "expired"};
                if (client.receipts.size() >= MaxReceipts)
                    return {"denied", "busy"};
                found = client.receipts.emplace(id, Record{}).first;
                found->second.key = key;
                found->second.destination = destination;
                found->second.expires = now + Lifetime;
                found->second.retainUntil = now + Lifetime + Retention;
            }
            Record& record = found->second;
            if (!record.terminal && now >= record.expires)
                Finish(record, {"denied", "expired"}, now);
            // Never use a historical arrival to authorize work at a new location/instance.
            if (record.reply.state == "arrived" && (!record.destination ||
                !position.At(*record.destination) || position.instance != record.arrivalInstance))
                Finish(record, {"denied", "moved_away"}, now);
            if (record.terminal)
                return record.reply;
            if (!destination)
                return Finish(record, {"denied", "invalid_destination"}, now);
            if (expansion < destination->firstExpansion || expansion > destination->lastExpansion)
                return Finish(record, {"denied", "wrong_expansion"}, now);
            if (!destination->available)
                return Finish(record, {"denied", "unavailable_destination"}, now);
            if (record.started)
            {
                if (position.At(*destination))
                {
                    record.arrivalInstance = position.instance;
                    return Finish(record, {"arrived", "ok"}, now);
                }
                return record.reply; // Pending go: check/status/replayed go never teleport again.
            }
            if (operation == "status")
                return record.reply; // A checked request stays ready; status cannot execute go.
            if (!eligibility.empty())
                return Finish(record, {"denied", eligibility}, now);
            if (now < client.nextTravel)
                return Finish(record, {"denied", "cooldown"}, now);
            if (operation == "check")
                return record.reply = {"ready", "ok"};

            // Each go revalidates via the current eligibility snapshot, not a cached check.
            record.started = true;
            record.expires = now + Lifetime;
            record.retainUntil = record.expires + Retention;
            record.reply = {"pending", "transfer"};
            if (!teleport())
                return Finish(record, {"denied", "transfer_failed"}, now);
            client.nextTravel = now + std::min(cooldown, MaxCooldown);
            return record.reply; // TeleportTo success is initiation, never arrival.
        }

        size_t OwnerCount() const { return clients.size(); }

    private:
        struct Record
        {
            std::string key;
            const Destination* destination = nullptr;
            Reply reply{"ready", "ok"};
            uint64_t expires = 0, retainUntil = 0;
            bool started = false, terminal = false;
            uint32_t arrivalInstance = 0;
        };
        struct Client
        {
            std::map<std::string, Record> receipts;
            uint64_t nextTravel = 0, nextCatalog = 0, nextCooldownSnapshot = 0, lastSeen = 0, rateWindow = 0;
            unsigned requests = 0;
        };
        std::map<Owner, Client> clients;
        uint64_t nextCleanup = 0;

        Reply Finish(Record& record, Reply reply, uint64_t now)
        {
            // Do not extend terminal receipts on repeated reads.
            if (!record.terminal)
                record.retainUntil = now + Retention;
            record.terminal = true;
            return record.reply = std::move(reply);
        }
        void Cleanup(uint64_t now)
        {
            if (now < nextCleanup)
                return;
            nextCleanup = now + 5;
            for (auto client = clients.begin(); client != clients.end();)
            {
                for (auto receipt = client->second.receipts.begin(); receipt != client->second.receipts.end();)
                    if (now >= receipt->second.retainUntil)
                        receipt = client->second.receipts.erase(receipt);
                    else
                        ++receipt;
                if (client->second.receipts.empty() && now >= client->second.nextTravel &&
                    now >= client->second.lastSeen + Retention)
                    client = clients.erase(client);
                else
                    ++client;
            }
        }
    };
}
#endif
