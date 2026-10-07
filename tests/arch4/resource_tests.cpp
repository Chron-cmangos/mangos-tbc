#include "Maps/GridMap.h"
#include "vmap/WorldModel.h"
#include "Database/DatabaseEnv.h"
#include "Database/SqlOperations.h"
#include "Memory/MemoryLedger.h"
#include <filesystem>
#include <fstream>
#include <chrono>
#include <iostream>
#include <cstring>
#include <cstdlib>

DatabaseType WorldDatabase, CharacterDatabase, LoginDatabase, LogsDatabase;
uint32 realmID = 0;
extern char const* MAP_MAGIC;
extern char const* MAP_VERSION_MAGIC;
#define CHECK(x) do { if (!(x)) { std::cerr << __LINE__ << ": " #x " failed\n"; std::abort(); } } while(false)
using ManTech::MemoryKind;
using ManTech::MemoryLedger;
int main()
{
    auto before = MemoryLedger::Read(MemoryKind::DatabaseWork);
    {
        SqlTransaction transaction;
        transaction.DelayExecute(new SqlPlainRequest("UPDATE synthetic SET value=1"));
        transaction.DelayExecute(new SqlPlainRequest("UPDATE synthetic SET value=2"));
        auto bytes=transaction.RetainedBytes();
        transaction.TrackMemory();
        transaction.TrackMemory(); // Queue ownership must be charged once.
        CHECK(MemoryLedger::Read(MemoryKind::DatabaseWork).bytes==before.bytes+bytes);
        CHECK(MemoryLedger::Read(MemoryKind::DatabaseWork).count==before.count+1);
    }
    CHECK(MemoryLedger::Read(MemoryKind::DatabaseWork).bytes==before.bytes);
    CHECK(MemoryLedger::Read(MemoryKind::DatabaseWork).count==before.count);
    before=MemoryLedger::Read(MemoryKind::Collision);
    {
        VMAP::WorldModel model;
        model.AccountMemory(); model.AccountMemory();
        CHECK(MemoryLedger::Read(MemoryKind::Collision).bytes>=before.bytes+sizeof(model));
        CHECK(MemoryLedger::Read(MemoryKind::Collision).count==before.count+1);
    }
    CHECK(MemoryLedger::Read(MemoryKind::Collision).bytes==before.bytes);
    CHECK(MemoryLedger::Read(MemoryKind::Collision).count==before.count);
    auto file=std::filesystem::temp_directory_path()/std::filesystem::path("arch4-grid-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count())+".map");
    GridMapFileHeader header{};
    std::memcpy(&header.mapMagic,MAP_MAGIC,4);
    std::memcpy(&header.versionMagic,MAP_VERSION_MAGIC,4);
    header.areaMapOffset=sizeof(header);
    header.areaMapSize=sizeof(GridMapAreaHeader)+256*sizeof(uint16);
    GridMapAreaHeader area{};
    std::memcpy(&area.fourcc,"AREA",4);
    uint16 areas[256]{};
    {
        std::ofstream out(file,std::ios::binary);
        out.write(reinterpret_cast<char*>(&header),sizeof(header));
        out.write(reinterpret_cast<char*>(&area),sizeof(area));
        out.write(reinterpret_cast<char*>(areas),sizeof(areas));
    }
    before=MemoryLedger::Read(MemoryKind::Terrain);
    {
        GridMap grid;
        for(unsigned i=0;i<20;++i) {
            CHECK(grid.loadData(file.string().c_str()));
            CHECK(grid.PayloadBytes()==sizeof(areas));
            CHECK(MemoryLedger::Read(MemoryKind::Terrain).bytes==before.bytes+sizeof(areas));
        }
        grid.unloadData(); grid.unloadData();
        CHECK(grid.PayloadBytes()==0);
        CHECK(MemoryLedger::Read(MemoryKind::Terrain).bytes==before.bytes);
    }
    CHECK(MemoryLedger::Read(MemoryKind::Terrain).bytes==before.bytes);
    std::filesystem::remove(file);
    std::cout << "SQL ownership, collision ownership and repeated terrain reload/unload accounting passed\n";
}
