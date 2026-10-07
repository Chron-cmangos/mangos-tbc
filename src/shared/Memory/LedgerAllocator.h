#ifndef MANTECH_LEDGER_ALLOCATOR_H
#define MANTECH_LEDGER_ALLOCATOR_H
#include "Memory/MemoryLedger.h"
#include <memory>
namespace ManTech {
template<class T, MemoryKind K> struct LedgerAllocator {
    using value_type=T;
    using is_always_equal=std::true_type;
    template<class U> struct rebind { using other=LedgerAllocator<U,K>; };
    LedgerAllocator() = default;
    template<class U> LedgerAllocator(LedgerAllocator<U,K> const&) noexcept {}
    T* allocate(std::size_t n) {
        auto p=std::allocator<T>{}.allocate(n);
        MemoryLedger::Add(K,n*sizeof(T)); return p;
    }
    void deallocate(T* p,std::size_t n) noexcept {
        std::allocator<T>{}.deallocate(p,n); MemoryLedger::Remove(K,n*sizeof(T));
    }
    template<class U> bool operator==(LedgerAllocator<U,K> const&) const noexcept { return true; }
    template<class U> bool operator!=(LedgerAllocator<U,K> const&) const noexcept { return false; }
};
}
#endif
