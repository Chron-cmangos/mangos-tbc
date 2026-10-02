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

        void Wait()
        {
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

    protected:
        MapUpdater& GetWorker() { return m_updater; }

    private:
        MapUpdater& m_updater;
};

class MapUpdateWorker : public Worker
{
    public:
        MapUpdateWorker(Map& map, uint32 diff, MapUpdater& updater) :
            Worker(updater), m_map(map), m_diff(diff)
        {}

        void execute() override
        {
            m_map.Update(m_diff);
            GetWorker().update_finished();
        }

    private:
        Map& m_map;
        uint32 m_diff;
};

class GridCrawler : public Worker
{
    public:
        GridCrawler(Map& map, std::vector<Cell>&& cells, WorldObjectUnSet& objects, uint32 diff,
            MapUpdateTaskGroup& group, MapUpdater& updater) :
            Worker(updater), m_map(map), m_cells(std::move(cells)), m_objects(objects), m_diff(diff), m_group(group)
        {}

        void execute() override
        {
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

        void execute() override
        {
            for (Object* object : m_objects)
                object->BuildUpdateData(m_updates);

            m_group.Done();
            GetWorker().update_finished();
        }

    private:
        std::vector<Object*> m_objects;
        UpdateDataMapType& m_updates;
        MapUpdateTaskGroup& m_group;
};

#ifdef ENABLE_PLAYERBOTS
class IdleBotAIUpdateWorker : public Worker
{
    public:
        IdleBotAIUpdateWorker(std::vector<std::pair<Player*, uint32>>&& updates,
            MapUpdateTaskGroup& group, MapUpdater& updater) :
            Worker(updater), m_updates(std::move(updates)), m_group(group)
        {}

        void execute() override
        {
            for (auto const& update : m_updates)
            {
                Player* player = update.first;
                if (player && player->IsInWorld())
                    player->UpdateAI(update.second, true);
            }

            m_group.Done();
            GetWorker().update_finished();
        }

    private:
        std::vector<std::pair<Player*, uint32>> m_updates;
        MapUpdateTaskGroup& m_group;
};
#endif
#endif //_MAP_WORKERS_H_INCLUDED