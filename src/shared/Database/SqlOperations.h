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

#ifndef __SQLOPERATIONS_H
#define __SQLOPERATIONS_H

#include "Common.h"
#include "Memory/MemoryLedger.h"
#include "Utilities/Callback.h"

#include <queue>
#include <vector>
#include <mutex>
#include <memory>

/// ---- BASE ---

class Database;
class SqlConnection;
class SqlDelayThread;
class SqlStmtParameters;

class SqlOperation
{
    std::size_t m_accountedBytes = 0;
    public:
        SqlOperation() = default;
        SqlOperation(SqlOperation const&) = delete;
        SqlOperation& operator=(SqlOperation const&) = delete;
        virtual void OnRemove() { delete this; }
        virtual bool Execute(SqlConnection* conn) = 0;
        virtual const char* DiagnosticKind() const { return "operation"; }
        virtual std::size_t RetainedBytes() const { return sizeof(*this); }
        void TrackMemory() { if (!m_accountedBytes) { m_accountedBytes = RetainedBytes(); ManTech::MemoryLedger::Add(ManTech::MemoryKind::DatabaseWork, m_accountedBytes); } }
        virtual ~SqlOperation() { if (m_accountedBytes) ManTech::MemoryLedger::Remove(ManTech::MemoryKind::DatabaseWork, m_accountedBytes); }
};

/// ---- ASYNC STATEMENTS / TRANSACTIONS ----

class SqlPlainRequest : public SqlOperation
{
    private:
        const char* m_sql;
    public:
        SqlPlainRequest(const char* sql) : m_sql(mangos_strdup(sql)) {}
        ~SqlPlainRequest() { char* tofree = const_cast<char*>(m_sql); delete[] tofree; }
        bool Execute(SqlConnection* conn) override;
        const char* DiagnosticKind() const override { return "statement"; }
        std::size_t RetainedBytes() const override { return sizeof(*this) + strlen(m_sql) + 1; }
};

class SqlTransaction : public SqlOperation
{
    private:
        std::vector<SqlOperation* > m_queue;

    public:
        SqlTransaction() {}
        ~SqlTransaction();

        void DelayExecute(SqlOperation* sql) { m_queue.push_back(sql); }

        bool Execute(SqlConnection* conn) override;
        const char* DiagnosticKind() const override { return "transaction"; }
        std::size_t RetainedBytes() const override { std::size_t bytes = sizeof(*this) + m_queue.capacity()*sizeof(SqlOperation*); for (auto op : m_queue) bytes += op->RetainedBytes(); return bytes; }
};

class SqlPreparedRequest : public SqlOperation
{
    public:
        SqlPreparedRequest(int nIndex, SqlStmtParameters* arg);
        ~SqlPreparedRequest();

        bool Execute(SqlConnection* conn) override;
        const char* DiagnosticKind() const override { return "prepared"; }
        std::size_t RetainedBytes() const override;

    private:
        const int m_nIndex;
        SqlStmtParameters* m_param;
};

/// ---- ASYNC QUERIES ----

class SqlQuery;                                             /// contains a single async query
class QueryResult;                                          /// the result of one
class SqlQueryHolder;                                       /// groups several async quries
class SqlQueryHolderEx;                                     /// points to a holder, added to the delay thread

class SqlResultQueue
{
    private:
        mutable std::mutex m_mutex;
        std::queue<std::unique_ptr<MaNGOS::IQueryCallback>> m_priorityQueue;
        std::queue<std::unique_ptr<MaNGOS::IQueryCallback>> m_queue;

    public:
        void Update(uint32 maxMilliseconds = 0);
        void Add(MaNGOS::IQueryCallback*, bool highPriority = false);
        size_t PendingCount() const;
};

class SqlQuery : public SqlOperation
{
    private:
        std::vector<char> m_sql;
        MaNGOS::IQueryCallback* const m_callback;
        SqlResultQueue* const m_queue;
        bool const m_highPriority;

    public:
        SqlQuery(const char* sql, MaNGOS::IQueryCallback* callback, SqlResultQueue* queue, bool highPriority = false)
            : m_sql(strlen(sql) + 1), m_callback(callback), m_queue(queue), m_highPriority(highPriority)
        {
            memcpy(&m_sql[0], sql, m_sql.size());
        }

        bool Execute(SqlConnection* conn) override;
        const char* DiagnosticKind() const override { return "query"; }
        std::size_t RetainedBytes() const override { return sizeof(*this) + m_sql.capacity(); }
};

class SqlQueryHolder
{
        friend class SqlQueryHolderEx;
    private:
        typedef std::pair<const char*, std::unique_ptr<QueryResult>> SqlResultPair;
        std::vector<SqlResultPair> m_queries;
    public:
        SqlQueryHolder() {}
        virtual ~SqlQueryHolder();
        std::size_t RetainedBytes() const { std::size_t bytes=sizeof(*this)+m_queries.capacity()*sizeof(SqlResultPair); for (auto const& q:m_queries) if (q.first) bytes+=strlen(q.first)+1; return bytes; }
        bool SetQuery(size_t index, const char* sql);
        bool SetPQuery(size_t index, const char* format, ...) ATTR_PRINTF(3, 4);
        void SetSize(size_t size);
        std::unique_ptr<QueryResult> GetResult(size_t index);
        void SetResult(size_t index, std::unique_ptr<QueryResult> queryResult);
        bool Execute(MaNGOS::IQueryCallback* callback, SqlDelayThread* thread, SqlResultQueue* queue, bool highPriority = false);
};

class SqlQueryHolderEx : public SqlOperation
{
    private:
        SqlQueryHolder* m_holder;
        MaNGOS::IQueryCallback* m_callback;
        SqlResultQueue* m_queue;
        bool m_highPriority;
    public:
        SqlQueryHolderEx(SqlQueryHolder* holder, MaNGOS::IQueryCallback* callback, SqlResultQueue* queue, bool highPriority = false)
            : m_holder(holder), m_callback(callback), m_queue(queue), m_highPriority(highPriority) {}
        bool Execute(SqlConnection* conn) override;
        const char* DiagnosticKind() const override { return "query_holder"; }
        std::size_t RetainedBytes() const override { return sizeof(*this) + (m_holder ? m_holder->RetainedBytes() : 0); }
};
#endif                                                      //__SQLOPERATIONS_H
