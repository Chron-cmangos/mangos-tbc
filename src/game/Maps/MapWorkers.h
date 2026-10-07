#include <chrono>
#include "Util/DevDiagnostics.h"
/*
* This file is part of the CMaNGOS Project. See AUTHORS file for Copyright information
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/

#ifndef _MAP_WORKERS_H_INCLUDED
#define _MAP_WORKERS_H_INCLUDED

#include "Grids/Cell.h"
#include "Grids/GridNotifiersImpl.h"
#include "MapUpdater.h"
#include "MotionGenerators/MovementGenerator.h"
#include "Entities/Object.h"
#include "Entities/UpdateData.h"
#include "Platform/Define.h"

#ifdef ENABLE_PLAYERBOTS
#include "playerbot/PlayerbotAI.h"
#endif

class MapUpdateTaskGroup
{
    public:
        void Add()
        {
            std::lock_guard<std::mutex> guard(m_lock);
            ++m_pending;
        }

        void Done()
        {
            std::lock_guard<std::mutex> guard(m_lock);
            MANGOS_ASSERT(m_pending > 0);
            if (--m_pending == 0)
                m_condition.notify_all();
        }

        void Wait(char const* diagnosticName = "map task group")
        {
            MANTECH_DIAG_SCOPE(TaskWait,1,diagnosticName);
            std::unique_lock<std::mutex> lock(m_lock);
            m_condition.wait(lock, [this]() { return m_pending == 0; });
        }

    private:
        std::mutex m_lock;
        std::condition_variable m_condition;
        size_t m_pending = 0;
};

class Worker
{
    public:
        Worker(MapUpdater& updater) : m_updater(updater) {}
        virtual ~Worker() = default;
        virtual void execute() {};
#ifdef MANTECH_DEV_DIAGNOSTICS
        std::uint64_t diagQueued=0,diagContext=ManTech::Diag::Context;
        virtual char const* DiagnosticName() const { return "other job"; }
#endif

    protected:
        MapUpdater& GetWorker() { return m_updater; }

    private:
        MapUpdater& m_updater;
};

class MapUpdateWorker : public Worker
{
    public:
        MapUpdateWorker(Map& map, uint32 diff, MapUpdater& updater, uint64* completedMicros = nullptr) :
            Worker(updater), m_map(map), m_diff(diff), m_completedMicros(completedMicros)
        {
#ifdef MANTECH_DEV_DIAGNOSTICS
            m_diagQueued=ManTech::Diag::Now();
            diagContext=(std::uint64_t(map.GetId())<<32)|map.GetInstanceId();
#endif
        }

        #ifdef MANTECH_DEV_DIAGNOSTICS
        char const* DiagnosticName() const override { return "map update"; }
#endif
        void execute() override
        {
#ifdef MANTECH_DEV_DIAGNOSTICS
            ManTech::Diag::Queue(m_diagQueued,m_map.GetId(),m_map.GetInstanceId());
#endif
            auto const started = std::chrono::steady_clock::now();
            m_map.Update(m_diff);
            if (m_completedMicros)
                *m_completedMicros = static_cast<uint64>(std::chrono::duration_cast<std::chrono::microseconds>(
                    std::chrono::steady_clock::now() - started).count());
            // Publish the estimate before the manager's existing completion barrier.
            GetWorker().update_finished();
        }

    private:
        Map& m_map;
        uint32 m_diff;
        uint64* m_completedMicros;
#ifdef MANTECH_DEV_DIAGNOSTICS
        std::uint64_t m_diagQueued=0;
#endif
};

class GridCrawler : public Worker
{
    public:
        GridCrawler(Map& map, std::vector<Cell>&& cells, WorldObjectUnSet& objects, uint32 diff,
            MapUpdateTaskGroup& group, MapUpdater& updater) :
            Worker(updater), m_map(map), m_cells(std::move(cells)), m_objects(objects), m_diff(diff), m_group(group)
        {}

        #ifdef MANTECH_DEV_DIAGNOSTICS
        char const* DiagnosticName() const override { return "grid objects"; }
#endif
        void execute() override
        {
    MANTECH_DIAG_CONTEXT(m_map.GetId(),m_map.GetInstanceId());
            MANTECH_DIAG_SCOPE(GridWorker,1,nullptr);
            MaNGOS::ObjectUpdater obj_updater(m_objects, m_diff);
            TypeContainerVisitor<MaNGOS::ObjectUpdater, GridTypeMapContainer  > grid_object_update(obj_updater);    // For creature
            TypeContainerVisitor<MaNGOS::ObjectUpdater, WorldTypeMapContainer > world_object_update(obj_updater);   // For pets

            for (auto &cell : m_cells)
            {
                m_map.Visit(cell, grid_object_update);
                m_map.Visit(cell, world_object_update);
            }

            m_group.Done();
            GetWorker().update_finished();
        }

    private:
        Map& m_map;
        std::vector<Cell> m_cells;
        WorldObjectUnSet& m_objects;
        uint32 m_diff;
        MapUpdateTaskGroup& m_group;
};


class ObjectUpdateBuildWorker : public Worker
{
    public:
        ObjectUpdateBuildWorker(std::vector<Object*>&& objects, UpdateDataMapType& updates,
            MapUpdateTaskGroup& group, MapUpdater& updater) :
            Worker(updater), m_objects(std::move(objects)), m_updates(updates), m_group(group)
        {}

        #ifdef MANTECH_DEV_DIAGNOSTICS
        char const* DiagnosticName() const override { return "object update packets"; }
#endif
        void execute() override
        {
#ifdef MANTECH_DEV_DIAGNOSTICS
            MANTECH_DIAG_CONTEXT(unsigned(m_diagContext>>32),unsigned(m_diagContext));
#endif
    MANTECH_DIAG_SCOPE(ObjectBuild,1,nullptr);
            for (Object* object : m_objects)
                object->BuildUpdateData(m_updates);

            m_group.Done();
            GetWorker().update_finished();
        }

    private:
#ifdef MANTECH_DEV_DIAGNOSTICS
        std::uint64_t m_diagContext=ManTech::Diag::Context;
#endif
        std::vector<Object*> m_objects;
        UpdateDataMapType& m_updates;
        MapUpdateTaskGroup& m_group;
};

#ifdef ENABLE_PLAYERBOTS
class IdleBotAIUpdateWorker : public Worker
{
    public:
        IdleBotAIUpdateWorker(IdleBotAIUpdateRequest const* updates, size_t count, uint32 jitterMs,
            MapUpdateTaskGroup& group, MapUpdater& updater) :
            Worker(updater), m_updates(updates), m_count(count), m_jitterMs(jitterMs), m_group(group)
        {}

        #ifdef MANTECH_DEV_DIAGNOSTICS
        char const* DiagnosticName() const override { return "idle bot batch"; }
#endif
        void execute() override
        {
#ifdef MANTECH_DEV_DIAGNOSTICS
            MANTECH_DIAG_CONTEXT(unsigned(m_diagContext>>32),unsigned(m_diagContext));
#endif
            for (size_t i = 0; i < m_count; ++i)
            {
                auto const& update = m_updates[i];
                Player* player = update.player;
                PlayerbotAI* ai = player ? player->GetPlayerbotAI() : nullptr;
                if (!ai || !ai->IsTransitionContextCurrent(update.transitionGeneration,
                    update.mapId, update.instanceId))
                {
                    PlayerbotAI::RecordDiscardedTransitionWork();
                    continue;
                }

                player->UpdateAI(update.elapsed, true, true);
                if (ai->IsTransitionContextCurrent(update.transitionGeneration,
                    update.mapId, update.instanceId))
                {
                    ai->ScheduleNextMinimalUpdate(player->GetGUIDLow(), m_jitterMs);
                }
                else
                    PlayerbotAI::RecordDiscardedTransitionWork();
            }

            m_group.Done();
            GetWorker().update_finished();
        }

    private:
#ifdef MANTECH_DEV_DIAGNOSTICS
        std::uint64_t m_diagContext=ManTech::Diag::Context;
#endif
        IdleBotAIUpdateRequest const* m_updates;
        size_t m_count;
        uint32 m_jitterMs;
        MapUpdateTaskGroup& m_group;
};
#endif
#endif //_MAP_WORKERS_H_INCLUDED
