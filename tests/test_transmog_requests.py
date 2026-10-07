"""Compile the real transmog request parser and equipment validation with fixtures."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
module = root / 'src/modules/transmog/src'
source = (module / 'TransmogModule.cpp').read_text()

def block(marker):
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 0
    for i in range(opening, len(source)):
        depth += (source[i] == '{') - (source[i] == '}')
        if depth == 0:
            return source[start:i+1]
    raise AssertionError(marker)

code = r'''
#include "TransmogRequest.h"
#include <cassert>
#include <algorithm>
#include <iterator>
#include <map>
using uint32=uint32_t; using uint8=uint8_t;
enum { EQUIPMENT_SLOT_END=19, INVENTORY_SLOT_BAG_0=0, INVTYPE_ROBE=20,
 INVTYPE_CHEST=5, UNIT_NPC_FLAG_GOSSIP=1 };
struct ItemPrototype { uint32 Class=4,SubClass=1,InventoryType=5,DisplayInfoID=10; };
struct Item { ItemPrototype proto; bool equipped=true;
 bool IsEquipped() { return equipped; } const ItemPrototype* GetProto() { return &proto; } };
struct Creature { uint32 entry=190010; uint32 GetEntry() { return entry; } };
struct Player { Item item; bool alive=true,combat=false,inRange=true;
 Creature npc; uint32 GetGUIDLow() const { return 7; }
 Item* GetItemByPos(int,uint8 slot) const { return slot==4?const_cast<Item*>(&item):nullptr; }
 bool IsAlive() { return alive; } bool IsInCombat() { return combat; }
 int GetSelectionGuid() { return 0; }
 Creature* GetNPCIfCanInteractWith(int,int) { return inRange?&npc:nullptr; }
};
struct ObjectMgr { ItemPrototype proto; const ItemPrototype* GetItemPrototype(uint32 entry) {
 return entry==100?&proto:nullptr; } } sObjectMgr;
struct Discovered { uint32 itemID=100; uint8 slots[4]={4,255,255,255}; };
class TransmogModule { public:
 std::map<uint32,std::map<uint32,Discovered>> playerDiscoveredTransmogs;
 bool valid=true;
 bool IsValidTransmog(const Player*,const ItemPrototype*) const { return valid; }
 bool ValidateRequest(const Player*,const std::vector<std::pair<uint32,uint32>>&) const;
 bool CanUseTransmogNpc(Player*) const;
};
'''
code += block('bool TransmogModule::ValidateRequest(')
code += block('bool TransmogModule::CanUseTransmogNpc(')
code += r'''
int main() {
 using cmangos_module::transmog_detail::ParseRequest;
 std::vector<std::pair<uint32,uint32>> slots;
 for (const char* bad : {"", "4", "4:", ":1", "-1:100", "4:-1", "4:1x",
     "4:100,", "4:100,4:0", "19:100", "256:100", "4:4294967296", "4:1:2", "4:100,,5:100"}) {
   assert(!ParseRequest(bad,slots)); assert(slots.empty());
 }
 assert(!ParseRequest(std::string(513,'1'),slots));
 assert(ParseRequest("4:100",slots));
 Player player; TransmogModule module;
 assert(!module.ValidateRequest(&player,slots)); // not learned
 module.playerDiscoveredTransmogs[7][10]=Discovered{};
 assert(module.ValidateRequest(&player,slots));
 module.valid=false; assert(!module.ValidateRequest(&player,slots)); module.valid=true;
 player.item.proto.SubClass=2; assert(!module.ValidateRequest(&player,slots));
 player.item.proto.SubClass=1; player.item.proto.InventoryType=8;
 assert(!module.ValidateRequest(&player,slots)); player.item.proto.InventoryType=20;
 assert(module.ValidateRequest(&player,slots)); // robe/chest match
 player.item.equipped=false; assert(!module.ValidateRequest(&player,slots)); player.item.equipped=true;
 assert(ParseRequest("4:0",slots)); assert(module.ValidateRequest(&player,slots));
 assert(ParseRequest("4:100,5:100",slots)); assert(!module.ValidateRequest(&player,slots));
 assert(ParseRequest("4:101",slots)); assert(!module.ValidateRequest(&player,slots));
 assert(module.CanUseTransmogNpc(&player));
 player.combat=true; assert(!module.CanUseTransmogNpc(&player)); player.combat=false;
 player.alive=false; assert(!module.CanUseTransmogNpc(&player)); player.alive=true;
 player.inRange=false; assert(!module.CanUseTransmogNpc(&player)); player.inRange=true;
 player.npc.entry=1; assert(!module.CanUseTransmogNpc(&player));
}
'''
with tempfile.TemporaryDirectory(prefix='transmog-request-') as temp:
    p=Path(temp)
    (p/'test.cpp').write_text(code)
    result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/I'+str(module),
        str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],capture_output=True,text=True)
    if result.returncode:
        raise SystemExit(result.stdout+result.stderr)
    subprocess.run([str(p/'test.exe')],check=True)
print('PASS: malformed/overflow/duplicate requests, discovery, equipment, restore and NPC gates')
