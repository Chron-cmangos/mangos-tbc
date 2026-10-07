"""Exercise the production WHO handler with packet/player fixtures.

Run in a Visual Studio developer shell. This verifies server response fields,
not rendering in an actual game client.
"""
from pathlib import Path
import subprocess, tempfile, sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
s=(root/'src/game/Entities/MiscHandler.cpp').read_text()
a=s.index('void WorldSession::HandleWhoOpcode(');p=s.index('{',a)+1;depth=1
while depth:
    depth+=(s[p]=='{')-(s[p]=='}');p+=1
method=s[a:p]
prefix=r'''
#include <cstdint>
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <algorithm>
#include <cwctype>
#include <iostream>
#include <cstdlib>
using uint32=uint32_t;using uint8=uint8_t;
using Team=int;enum AccountTypes{SEC_PLAYER=0,SEC_ADMINISTRATOR=3};
constexpr uint32 MAX_LEVEL=80,STRONG_MAX_LEVEL=255,SMSG_WHO=1;
enum{CONFIG_BOOL_ALLOW_TWO_SIDE_WHO_LIST,CONFIG_UINT32_GM_LEVEL_IN_WHO_LIST,CONFIG_UINT32_MAX_WHOLIST_RETURNS};
#define DEBUG_LOG(...) ((void)0)
#define CHECK(x) do{if(!(x)){std::cerr<<"FAIL: " #x "\n";std::exit(2);}}while(0)
bool Utf8toWStr(const std::string&s,std::wstring&w){w.assign(s.begin(),s.end());return true;}
void wstrToLower(std::wstring&w){std::transform(w.begin(),w.end(),w.begin(),::towlower);}
bool Utf8FitTo(const std::string&s,const std::wstring&w){std::wstring t;Utf8toWStr(s,t);wstrToLower(t);return t.find(w)!=std::wstring::npos;}
struct WorldPacket{
 std::vector<uint32> input;std::vector<std::string> textInput;size_t n=0,t=0;
 uint32 counts[2]={0,0};std::vector<std::string> strings;
 WorldPacket(uint32=0,uint32=0){}
 WorldPacket& operator>>(uint32&v){v=input.at(n++);return *this;}
 WorldPacket& operator>>(std::string&v){v=textInput.at(t++);return *this;}
 template<class T>WorldPacket& operator<<(const T&){return *this;}
 WorldPacket& operator<<(const std::string&s){strings.push_back(s);return *this;}
 void put(uint32 offset,uint32 value){counts[offset/4]=value;}
};
struct Config{bool enabled=true;bool GetBoolDefault(const char*,bool){return enabled;}}sConfig;
struct World{bool both=false;uint32 limit=49;uint32 getConfig(int key){return key==CONFIG_BOOL_ALLOW_TWO_SIDE_WHO_LIST?both:key==CONFIG_UINT32_GM_LEVEL_IN_WHO_LIST?3:limit;}}sWorld;
struct SessionInfo{AccountTypes security=SEC_PLAYER;AccountTypes GetSecurity(){return security;}};
struct Player{
 std::string name;Team team=1;uint32 level=40,klass=1,race=1;bool world=true,visible=true,bot=false;SessionInfo session;
 Team GetTeam(){return team;}SessionInfo* GetSession(){return &session;}bool IsInWorld(){return world;}
 bool IsVisibleGloballyFor(Player*){return visible;}uint32 GetLevel(){return level;}uint32 getClass(){return klass;}
 uint32 getRace(){return race;}uint32 GetZoneId(){return 1;}uint8 getGender(){return 0;}
 std::string GetName(){return name;}uint32 GetGuildId(){return 1;}
};
template<class T>struct HashMapHolder{using MapType=std::map<uint32,T*>;};
struct Accessor{HashMapHolder<Player>::MapType players;auto& GetPlayers(){return players;}}sObjectAccessor;
struct Tickets{bool HookGMTicketWhoQuery(const std::string&,Player*){return false;}}sTicketMgr;
struct Guilds{std::string GetGuildNameById(uint32){return "guild";}}sGuildMgr;
struct AreaTableEntry{std::string area_name[1]={"zone"};};
const AreaTableEntry* GetAreaEntryByAreaID(uint32){static AreaTableEntry area;return &area;}
struct WorldSession{
 Player* _player;AccountTypes security=SEC_PLAYER;WorldPacket sent;
 Player* GetPlayer(){return _player;}AccountTypes GetSecurity(){return security;}int GetSessionDbcLocale(){return 0;}
 void SendPacket(const WorldPacket&packet){sent=packet;}void HandleWhoOpcode(WorldPacket&);
};
WorldPacket query(std::string name="",uint32 low=1,uint32 high=80,uint32 classes=~0u){
 WorldPacket p;p.input={low,high,~0u,classes,0,0};p.textInput={name,""};return p;
}
'''
suffix=r'''
int main(){
 std::vector<std::unique_ptr<Player>> players;
 for(uint32 i=0;i<6000;++i){auto p=std::make_unique<Player>();p->team=i<3000?1:2;
  p->name=(p->team==1?"Alliance":"Horde")+std::to_string(i);p->bot=i>1;
  sObjectAccessor.players[i]=p.get();players.push_back(std::move(p));}
 Player loading;loading.name="Loading";loading.world=false;sObjectAccessor.players[6000]=&loading;
 // Hidden names still contribute to the requested aggregate, without being exposed.
 players[1]->visible=false;
 WorldSession session{players[0].get()};
 auto p=query();session.HandleWhoOpcode(p);
 CHECK(session.sent.counts[0]==49&&session.sent.counts[1]==6000);
 CHECK(session.sent.strings.size()==98);
 for(size_t i=0;i<session.sent.strings.size();i+=2)CHECK(session.sent.strings[i].find("Alliance")==0&&session.sent.strings[i]!="Alliance1");
 // Filters narrow only the names; all-online total survives exact, empty and level/class searches.
 p=query("Alliance0");session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==1&&session.sent.counts[1]==6000);
 p=query("Horde3000");session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==0&&session.sent.counts[1]==6000&&session.sent.strings.empty());
 p=query("",50,60);session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==0&&session.sent.counts[1]==6000);
 p=query("",1,80,1<<2);session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==0&&session.sent.counts[1]==6000);
 sWorld.both=true;p=query("Horde3000");session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==1&&session.sent.counts[1]==6000);
 sWorld.both=false;session.security=SEC_ADMINISTRATOR;p=query("Horde3000");session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==0&&session.sent.counts[1]==6000);
 // Turning population mode off retains native matching counts and GM cross-faction lookup.
 sConfig.enabled=false;p=query("Horde3000");session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==1&&session.sent.counts[1]==1);
 session.security=SEC_PLAYER;p=query("Horde3000");session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==0&&session.sent.counts[1]==0);
 p=query();session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==49&&session.sent.counts[1]==49);
 sWorld.limit=0;p=query();session.HandleWhoOpcode(p);CHECK(session.sent.counts[0]==49&&session.sent.counts[1]==2999);
 std::cout<<"PASS: global 6000-character total, bots, 49-row limit, filtered/empty searches, faction toggle, GM mode, native fallback\n";
}
'''
with tempfile.TemporaryDirectory(prefix='who-population-') as tmp:
    folder=Path(tmp);(folder/'test.cpp').write_text(prefix+method+suffix)
    result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=folder,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    result=subprocess.run([str(folder/'test.exe')],cwd=folder,capture_output=True,text=True)
    print(result.stdout+result.stderr,end='')
    raise SystemExit(result.returncode)
