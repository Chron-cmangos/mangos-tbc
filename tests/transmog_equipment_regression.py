from pathlib import Path
import sys,re,subprocess,tempfile
r=Path(sys.argv[1])
def block(s,signature):
 start=s.index(signature);b=s.index('{',start);level=1;i=b+1
 while level:
  if s[i]=='{':level+=1
  elif s[i]=='}':level-=1
  i+=1
 return s[start:i]
source=(r/'src/modules/transmog/src/TransmogModule.cpp').read_text()
fn=block(source,'void TransmogModule::SendEquipmentStatus(')
assert 'SetEntry(' not in source and 'SetUInt32Value(ITEM_FIELD_ENTRY' not in source
native=block((r/'src/game/Entities/Item.cpp').read_text(),'void AddItemsSetItem(')
assert 'item->GetProto()' in native and 'proto->ItemSet' in native
inspect=block((r/'src/game/Entities/MiscHandler.cpp').read_text(),'void WorldSession::HandleInspectOpcode(')
assert inspect.index('CanAttack(plr)')<inspect.index('OnInspectEquipment')<inspect.index('SendPacket(data)')
struct=block((r/'src/game/Server/DBCStructure.h').read_text(),'struct ItemSetEntry')+';'
fmt=re.search(r'ItemSetEntryfmt\[\]\s*=\s*"([^"]+)"',(r/'src/game/Server/DBCfmt.h').read_text()).group(1)
langs=8 if r.name=='classic' else 16
assert fmt=='d'+'s'*langs+'x'+'i'*35
code=r'''
#include <cassert>
#include <map>
#include <string>
#include <vector>
#include <sstream>
#include <cstdio>
using uint32=unsigned;using uint8=unsigned char;
__STRUCT__
struct ItemPrototype{unsigned ItemSet=208;char*Name1=const_cast<char*>("Real piece");};
struct Item{unsigned id;ItemPrototype proto;unsigned GetEntry()const{return id;}const ItemPrototype*GetProto()const{return &proto;}};
struct ItemSetEffect{unsigned item_count=4;};struct Session{std::string remote="human";const std::string&GetRemoteAddress(){return remote;}};
constexpr unsigned EQUIPMENT_SLOT_START=0,EQUIPMENT_SLOT_END=19,INVENTORY_SLOT_BAG_0=0;
struct Player{mutable Session session;ItemSetEffect effect;Item pieces[4]={{16856},{16858},{16857},{16860}};
Session*GetSession()const{return &session;}unsigned GetGUIDLow(){return 17872;}const char*GetName(){return "Unclebud";}
const Item*GetItemByPos(unsigned,unsigned slot){return slot<4?&pieces[slot]:nullptr;}ItemSetEffect*GetItemSetEffect(unsigned){return &effect;}};
struct Store{ItemSetEntry set{};const ItemSetEntry*LookupEntry(unsigned){return &set;}}sItemSetStore;
struct ObjectMgr{ItemPrototype proto;const ItemPrototype*GetItemPrototype(unsigned){return &proto;}}sObjectMgr;
namespace helper{template<class...A>std::string FormatString(const char*f,A...a){char b[512];snprintf(b,sizeof(b),f,a...);return b;}}
std::vector<std::string>messages;void SendAddOnMessage(const Player*,const char*p,const std::string&m){assert(std::string(p)=="mantechequip");assert(m.size()<240);messages.push_back(m);}
struct TransmogModule{unsigned equipmentSerial=0;unsigned GetTransmogAppearance(const Item*i){return i->id==16858||i->id==16857?999:0;}void SendEquipmentStatus(const Player*,Player*,const char*);};
__FUNCTION__
int main(){Player p;TransmogModule m;sItemSetStore.set.name[0]=const_cast<char*>("Lawbringer");
unsigned ids[8]={16853,16854,16855,16856,16857,16858,16859,16860};for(unsigned i=0;i<8;++i)sItemSetStore.set.itemId[i]=ids[i];
 sItemSetStore.set.spells[0]=1;sItemSetStore.set.items_to_triggerspell[0]=3;
 m.SendEquipmentStatus(&p,&p,"self");bool count=false,belt=false,bonus=false;unsigned slots=0;
 for(auto&s:messages){if(s=="GearSet:1:208:4:4:8:Lawbringer")count=true;if(s=="GearSlot:1:2:16858:999:208")belt=true;if(s=="GearBonus:1:208:3")bonus=true;if(s.find("GearSlot:")==0)++slots;}
 assert(count&&belt&&bonus&&slots==19&&messages.back()=="GearEnd:1");
 p.effect.item_count=0;messages.clear();m.SendEquipmentStatus(&p,&p,"inspect");bool inactive=false;for(auto&s:messages)if(s=="GearSet:2:208:4:0:8:Lawbringer")inactive=true;assert(inactive);
 messages.clear();p.session.remote="disconnected/bot";m.SendEquipmentStatus(&p,&p,"self");assert(messages.empty());}
'''.replace('__STRUCT__',struct).replace('__FUNCTION__',fn)
with tempfile.TemporaryDirectory(prefix='transmog-equipment-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS native true gear metadata, four real/two cosmetic set pieces, active native set counts, bounded inventory-only snapshot, inspect permissions and unchanged native set calculation/DBC column mappings')
