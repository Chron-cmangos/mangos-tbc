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

#include "MapUpdater.h"
#include "MapWorkers.h"
#include <algorithm>

MapUpdater::MapUpdater(size_t num_threads) : _cancelationToken(false), pending_requests(0), peak_pending_requests(0)
{
    for (size_t i = 0; i < num_threads; ++i)
        _workerThreads.push_back(std::thread(&MapUpdater::WorkerThread, this));
}

void MapUpdater::activate(size_t num_threads)
{
    if (activated())
        return;

    for (size_t i = 0; i < num_threads; ++i)
        _workerThreads.push_back(std::thread(&MapUpdater::WorkerThread, this));
}

void MapUpdater::deactivate()
{
    _cancelationToken = true;

    _queue.Cancel();

    for (auto& thread : _workerThreads)
        thread.join();
}

void MapUpdater::wait()
{
    MANTECH_DIAG_SCOPE(MapBarrier,1,nullptr);
    std::unique_lock<std::mutex> lock(_lock);

    while (pending_requests > 0)
        _condition.wait(lock);
}

void MapUpdater::join()
{
    wait();
    deactivate();
}

bool MapUpdater::activated()
{
    return _workerThreads.size() > 0;
}

void MapUpdater::update_finished()
{
    std::lock_guard<std::mutex> lock(_lock);

    --pending_requests;
    _condition.notify_all();
}

void MapUpdater::schedule_update(Worker* worker)
{
    std::lock_guard<std::mutex> lock(_lock);

    ++pending_requests;
    peak_pending_requests = std::max(peak_pending_requests, pending_requests);
    #ifdef MANTECH_DEV_DIAGNOSTICS
    worker->diagQueued=ManTech::Diag::Now();
#endif
    _queue.Push(std::move(worker));
}

size_t MapUpdater::GetPendingRequests()
{
    std::lock_guard<std::mutex> lock(_lock);
    return pending_requests;
}

size_t MapUpdater::GetQueuedRequests()
{
    return _queue.Size();
}

size_t MapUpdater::ConsumePeakPendingRequests()
{
    std::lock_guard<std::mutex> lock(_lock);
    size_t const peak = peak_pending_requests;
    peak_pending_requests = pending_requests;
    return peak;
}

void MapUpdater::WorkerThread()
{
    while (true)
    {
        Worker* request = nullptr;

        _queue.WaitAndPop(request);

        if (_cancelationToken)
        {
            delete request;
            return;
        }

        {
#ifdef MANTECH_DEV_DIAGNOSTICS
            MANTECH_DIAG_CONTEXT(unsigned(request->diagContext>>32),unsigned(request->diagContext));
            ManTech::Diag::JobQueued(request->diagQueued,request->DiagnosticName());
            MANTECH_DIAG_SCOPE(JobExecute,1,request->DiagnosticName());
#endif
            request->execute();
        }

        delete request;
    }
}
