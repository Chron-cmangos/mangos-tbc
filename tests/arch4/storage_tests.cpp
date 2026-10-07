#include "Memory/LazyStorage.h"
#include "Memory/ScratchLease.h"
#include <map>
#include <list>
#include <thread>
#include <iostream>
#include <cstdlib>
#define CHECK(x) do { if (!(x)) { std::cerr << "Failed: " #x << '\n'; std::abort(); } } while (0)
int main() {
    using namespace ManTech;
    auto before=MemoryLedger::Read(MemoryKind::OptionalState);
    {
        LazyStorageArray<std::map<int,int>,8> maps;
        CHECK(maps.Read(2).empty()); CHECK(MemoryLedger::Read(MemoryKind::OptionalState).bytes==before.bytes);
        auto const& stable=static_cast<decltype(maps) const&>(maps)[2]; auto end=stable.end();
        maps[2].emplace(3,42); CHECK(stable.at(3)==42);CHECK(end==stable.end());
        maps[2].clear();CHECK(end==stable.end());
        std::thread a([&]{ for(int i=0;i<1000;++i) (void)static_cast<decltype(maps) const&>(maps)[5]; });
        std::thread b([&]{ for(int i=0;i<1000;++i) (void)static_cast<decltype(maps) const&>(maps)[5]; });
        a.join();b.join();CHECK(MemoryLedger::Read(MemoryKind::OptionalState).count==before.count+2);
    }
    CHECK(MemoryLedger::Read(MemoryKind::OptionalState).bytes==before.bytes);
    auto scratchBefore=MemoryLedger::Read(MemoryKind::PathScratch).bytes;
    std::thread worker([]{
        void* outerPointer;
        { ScratchLease<float> outer(200);outer.Get()[0]=42;outerPointer=outer.Get().data();
          { ScratchLease<float> nested(200);CHECK(nested.Get().data()!=outerPointer);nested.Get()[0]=7; }
          CHECK(outer.Get()[0]==42); }
        { ScratchLease<float> reused(200);CHECK(reused.Get().data()==outerPointer); }
        { ScratchLease<float> oversized(65536);CHECK(oversized.Get().size()>=65536); }
        CHECK(MemoryLedger::Read(MemoryKind::PathScratch).bytes==0);
    }); worker.join();
    CHECK(MemoryLedger::Read(MemoryKind::PathScratch).bytes==scratchBefore);
    std::cout<<"Optional container lifetime, nested scratch isolation, byte cap and thread teardown passed\n";
}
