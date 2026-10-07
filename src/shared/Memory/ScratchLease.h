#ifndef MANTECH_SCRATCH_LEASE_H
#define MANTECH_SCRATCH_LEASE_H
#include "Memory/LedgerAllocator.h"
#include <vector>
namespace ManTech {
// Scratch never escapes its synchronous call. Nested calls get independent
// storage. At most 64 KiB per element type is retained by each worker thread;
// unusually large temporary buffers are released when their lease ends.
template<class T> class ScratchLease {
public:
    using Buffer=std::vector<T,LedgerAllocator<T,MemoryKind::PathScratch>>;
private:
    struct State { Buffer buffer; bool borrowed=false; };
    inline static thread_local State cache;
    Buffer local;
    Buffer* buffer;
    bool borrowed;
public:
    explicit ScratchLease(std::size_t n) : buffer(cache.borrowed ? &local : &cache.buffer), borrowed(!cache.borrowed) {
        if (borrowed) cache.borrowed=true;
        try { if (buffer->size()<n) buffer->resize(n); }
        catch (...) { if (borrowed) cache.borrowed=false; throw; }
    }
    ScratchLease(ScratchLease const&)=delete;
    ScratchLease& operator=(ScratchLease const&)=delete;
    ~ScratchLease() {
        if (borrowed) {
            if (buffer->capacity()*sizeof(T)>64*1024) Buffer{}.swap(*buffer);
            cache.borrowed=false;
        }
    }
    Buffer& Get() { return *buffer; }
};
}
#endif
