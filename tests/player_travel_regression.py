"""Compile the actual .tp adapter and transaction service with controlled external APIs.

Run in a compiler environment: python player_travel_regression.py <core-root>
Uses cl on Windows, c++ elsewhere. Native entry/pathfinding and a real client are
not simulated by these tests. Run a full core build separately.
"""
from pathlib import Path
import json,re,subprocess,sys,tempfile,os
root=Path(sys.argv[1])
source=(root/'src/game/Chat/PlayerTravel.cpp').read_text()
assert re.search(r'duration_cast<std::chrono::seconds>\s*\(\s*std::chrono::steady_clock::now', source)
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include "'))
source=re.sub(r'uint64_t TravelNow\(\)\s*\{.*?\n    \}', 'uint64_t TravelNow() { return fakeNow; }', source, count=1,flags=re.S)
manifest=json.loads((root/'docs/PLAYER-TRAVEL-DESTINATIONS.json').read_text())
era=manifest['expansion']; expansion=('classic','tbc','wotlk').index(era)
chat=(root/'src/game/Chat/Chat.cpp').read_text()
assert re.search(r'\{ "tp",\s*SEC_PLAYER,\s*false,\s*&ChatHandler::HandlePlayerTravelCommand',chat)
assert re.search(r'\{ "tele",\s*SEC_MODERATOR,\s*true,\s*nullptr,\s*"", teleCommandTable',chat)
assert re.search(r'\{ "tp",\s*SEC_MODERATOR,\s*false,\s*&ChatHandler::HandleModifyTalentCommand',chat)
assert 'PlayerTravel.Enabled = 0' in (root/'src/mangosd/mangosd.conf.dist.in').read_text()
opcode=(root/'src/game/Server/Opcodes.cpp').read_text()
assert re.search(r'CMSG_MESSAGECHAT.*PROCESS_THREADUNSAFE',opcode)
map_source=(root/'src/game/Maps/Map.cpp').read_text()
add=map_source[map_source.index('bool DungeonMap::Add(Player* player)'):]
add=add[:add.index('void DungeonMap::Update')]
assert add.index('CanEnter(player)') < add.index('Map::Add(player);') < add.index('player->RecordDungeonTravelVisit();') < add.rindex('return true;')
assert 'DELETE FROM character_dungeon_travel' in (root/'src/game/Entities/Player.cpp').read_text()
player_source=(root/'src/game/Entities/Player.cpp').read_text()
copy=player_source.index('"INSERT INTO account_dungeon_travel')
delete=player_source.index('"DELETE FROM character_dungeon_travel')
assert player_source.rfind('CharacterDatabase.BeginTransaction();',0,copy)>=0
assert copy<delete<player_source.index('CharacterDatabase.CommitTransaction();',delete)
assert 'DELETE FROM account_dungeon_travel' not in player_source
assert 'DELETE FROM account_dungeon_travel' in (root/'src/game/Accounts/AccountMgr.cpp').read_text()
assert 'PRIMARY KEY (account, destination)' in (root/'sql/custom/characters/20260909_02_account_dungeon_travel.sql').read_text()

assert 'PRIMARY KEY (guid, destination)' in (root/'sql/custom/characters/20260909_01_player_dungeon_travel.sql').read_text()
assert 'GetSelectedPlayer' not in source and 'SetSecurity' not in source and 'HandleGoHelper' not in source
assert len([d for d in manifest['destinations'] if d['available']])==(32,57,80)[expansion]

stubs=r'''
#include <cassert>
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <cstdint>
#include <set>
#include <memory>
#include <regex>
#include <cstdarg>
#include "PlayerTravel.h"
#include "PlayerTravelDestinations.h"
using uint32=uint32_t;
uint64_t fakeNow=100;
enum {UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1,CONFIG_BOOL_INSTANCE_IGNORE_LEVEL,
 CONFIG_BOOL_BATTLEFIELD_WG_ENABLED,BATTLEFIELD_WG,BF_STATUS_COOLDOWN,BF_STATUS_IN_PROGRESS};
enum AreaLockStatus {AREA_LOCKSTATUS_OK,AREA_LOCKSTATUS_TOO_LOW_LEVEL,AREA_LOCKSTATUS_RAID_LOCKED,
 AREA_LOCKSTATUS_ZONE_IN_COMBAT,AREA_LOCKSTATUS_INSTANCE_IS_FULL,AREA_LOCKSTATUS_HAS_BIND,AREA_LOCKSTATUS_OTHER};
struct MapEntry {bool dungeon=false;bool IsDungeon()const{return dungeon;}bool IsRaid()const{return dungeon;}};
struct Map:MapEntry{};
struct MapStore{std::map<uint32,MapEntry> maps;const MapEntry* LookupEntry(uint32 id){auto it=maps.find(id);return it==maps.end()?nullptr:&it->second;}} sMapStore;
struct AreaTrigger {uint32 target_mapId=0,requiredLevel=1;};
struct ObjectMgr{std::map<uint32,AreaTrigger> entries;const AreaTrigger* GetAreaTrigger(uint32 id){auto it=entries.find(id);return it==entries.end()?nullptr:&it->second;}}sObjectMgr;
struct Config{bool enabled=true;int cooldown=300;bool GetBoolDefault(const char*,bool){return enabled;}int GetIntDefault(const char*,int){return cooldown;}}sConfig;
struct World{bool ignoreLevel=false,battlefield=true;bool getConfig(int key){return key==CONFIG_BOOL_INSTANCE_IGNORE_LEVEL?ignoreLevel:battlefield;}}sWorld;
struct Battlefield{int status=BF_STATUS_COOLDOWN,team=0;int GetDefender(){return team;}int GetBattlefieldStatus(){return status;}};
struct Outdoor{Battlefield battlefield;bool exists=true;Battlefield* GetBattlefieldById(int){return exists?&battlefield:nullptr;}}sOutdoorPvPMgr;
struct Group{uint32 leader=1;bool IsLeader(uint32 guid){return guid==leader;}};

struct Field{std::string value;std::string GetString(){return value;}};
struct QueryResult{std::vector<Field> rows;size_t index=0;Field* Fetch(){return &rows[index];}bool NextRow(){return ++index<rows.size();}};
struct Database{
 std::map<uint32,std::set<std::string>> persisted,legacy;unsigned reads=0,writes=0;bool readOK=true,writeOK=true;
 std::unique_ptr<QueryResult> PQuery(const char* sql,...){assert(std::string(sql).find("UNION ALL SELECT ''")!=std::string::npos);++reads;
  assert(std::string(sql).find("account_dungeon_travel WHERE account = %u")!=std::string::npos);
  va_list args;va_start(args,sql);uint32 account=va_arg(args,uint32);
  assert(va_arg(args,uint32)==account&&va_arg(args,uint32)==account);va_end(args);if(!readOK)return nullptr;
  auto out=std::make_unique<QueryResult>();for(const auto& key:persisted[account])out->rows.push_back({key});for(const auto& key:legacy[account])out->rows.push_back({key});out->rows.push_back({""});return out;}
 bool DirectExecute(const char* sql){++writes;if(!writeOK)return false;std::string text=sql;
  assert(text.find("INSERT IGNORE INTO account_dungeon_travel")==0);
  std::regex row("\\(([0-9]+),'([a-z0-9_]+)',UNIX_TIMESTAMP\\(\\)\\)");
  auto begin=std::sregex_iterator(text.begin(),text.end(),row);assert(begin!=std::sregex_iterator{});
  for(auto it=begin;it!=std::sregex_iterator{};++it)persisted[std::stoul((*it)[1])].insert((*it)[2]);return true;}
}CharacterDatabase;
struct Player{
 bool world=true,transfer=false,alive=true,real=true,gm=false,combat=false,taxi=false,transport=false,arena=false,bg=false,charm=false,rooted=false,controlled=false,nativeSuccess=true;
 uint32 id=1,mapId=0,instance=0,level=80;float x=0,y=0,z=0;int team=0;unsigned teleports=0,lockChecks=0;
 struct Identity{uint32 account=1;uint32 GetAccountId(){return account;}}session;
 Identity* GetSession(){return &session;}
 std::set<std::string> m_dungeonTravelUnlocks;
 bool LoadDungeonTravelUnlocks();bool HasDungeonTravelUnlock(const char* key)const{return m_dungeonTravelUnlocks.count(key)!=0;}void RecordDungeonTravelVisit();
 AreaLockStatus lock=AREA_LOCKSTATUS_OK;const AreaTrigger* lastEntry=nullptr;Group* group=nullptr;Map map;
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool IsAlive(){return alive;}bool isRealPlayer(){return real;}
 bool IsGameMaster(){return gm;}bool IsInCombat(){return combat;}bool IsTaxiFlying(){return taxi;}void* GetTransport(){return transport?this:nullptr;}
 bool InArena(){return arena;}bool InBattleGround(){return bg;}Map* GetMap(){return &map;}bool HasCharmer(){return charm;}bool IsRooted(){return rooted;}
 bool hasUnitState(int){return controlled;}Group* GetGroup(){return group;}uint32 GetObjectGuid(){return id;}uint32 GetGUIDLow(){return id;}
 uint32 GetMapId(){return mapId;}uint32 GetInstanceId(){return instance;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 uint32 GetLevel(){return level;}int GetDifficulty(bool){return 0;}int GetTeam(){return team;}
 AreaLockStatus GetAreaTriggerLockStatus(const AreaTrigger*,uint32&,bool force){assert(force);++lockChecks;return lock;}
 AreaLockStatus GetAreaTriggerLockStatus(const AreaTrigger*,int,uint32&,bool force){assert(force);++lockChecks;return lock;}
 bool TeleportTo(uint32 map,float a,float b,float c,float,uint32 options,const AreaTrigger* entry){assert(options==0);++teleports;lastEntry=entry;
 if(!nativeSuccess)return false;transfer=true;world=false;mapId=map;x=a;y=b;z=c;return true;}
};
struct WorldSession{Player* player=nullptr;uint32 account=1;Player* GetPlayer(){return player;}uint32 GetAccountId(){return account;}};
std::vector<std::string> messages;
struct ChatHandler{WorldSession* m_session=nullptr;bool HandlePlayerTravelCommand(char*);void SendSysMessage(const char* s){messages.emplace_back(s);}};
'''

tests=r'''
void reset(){travel=PlayerTravel::Service{};messages.clear();fakeNow=100;sConfig={};sWorld={};sOutdoorPvPMgr={};sObjectMgr.entries.clear();sMapStore.maps.clear();CharacterDatabase={};
 for(const auto& d:PlayerTravel::Destinations)if(d.available)CharacterDatabase.persisted[1].insert(d.key);
 for(auto const& d:PlayerTravel::Destinations)if(d.available){sMapStore.maps[d.map].dungeon=d.map==d.instanceMap;
 if(d.entryTrigger)sObjectMgr.entries[d.entryTrigger]={d.instanceMap,1};}}
std::string command(Player& p,std::string args,uint32 account=1){WorldSession session;session.account=account;p.session.account=account;session.player=&p;ChatHandler handler;handler.m_session=&session;
 auto n=messages.size();assert(handler.HandlePlayerTravelCommand(&args[0]));assert(messages.size()>n);return messages.back();}
bool ends(std::string text,std::string suffix){return text.size()>=suffix.size()&&text.substr(text.size()-suffix.size())==suffix;}
void arrive(Player& p){p.transfer=false;p.world=true;}
int main(){
 using namespace PlayerTravel;
 reset();Player p;
 assert(command(p,"v1 one status deadmines")=="PBTP 1 one deadmines denied expired");assert(!p.teleports);
 assert(ends(command(p,"v1 one go deadmines"),"denied expired"));assert(!p.teleports);
 assert(ends(command(p,"v2 one check deadmines"),"unsupported version"));
 assert(ends(command(p,"v1 id check bad/key"),"denied arguments"));
 assert(ends(command(p,"v1 id extra deadmines tail"),"denied arguments"));
 reset();p={};assert(ends(command(p,"v1 one check deadmines"),"ready ok"));assert(!p.teleports);
 assert(ends(command(p,"v1 one status deadmines"),"ready ok"));assert(!p.teleports);
 assert(ends(command(p,"v1 one go deadmines"),"pending transfer"));assert(p.teleports==1);
 assert(ends(command(p,"v1 one go deadmines"),"pending transfer"));assert(p.teleports==1);
 assert(ends(command(p,"v1 one status deadmines"),"pending transfer"));
 fakeNow+=2;arrive(p);assert(ends(command(p,"v1 one status deadmines"),"arrived ok"));
 p.instance++;assert(ends(command(p,"v1 one status deadmines"),"denied moved_away"));assert(p.teleports==1);
 reset();p={};command(p,"v1 one check deadmines");p.combat=true;
 assert(ends(command(p,"v1 one go deadmines"),"denied combat"));p.combat=false;
 assert(ends(command(p,"v1 one go deadmines"),"denied combat"));assert(!p.teleports);
 reset();p={};command(p,"v1 one check deadmines");assert(ends(command(p,"v1 one go uldaman"),"denied request_conflict"));assert(!p.teleports);
 reset();p={};command(p,"v1 one check deadmines");fakeNow+=60;
 assert(ends(command(p,"v1 one go deadmines"),"denied expired"));assert(ends(command(p,"v1 one check deadmines"),"denied expired"));assert(!p.teleports);
 reset();p={};command(p,"v1 one check deadmines");p.nativeSuccess=false;
 assert(ends(command(p,"v1 one go deadmines"),"denied transfer_failed"));command(p,"v1 one go deadmines");assert(p.teleports==1);
 reset();p={};command(p,"v1 one check deadmines");command(p,"v1 one go deadmines");arrive(p);
 assert(ends(command(p,"v1 two check uldaman"),"denied cooldown"));assert(p.teleports==1);
 // Each valid alias routes through the real parser into the exact whitelist coordinates.
 for(const auto& d:Destinations){
  reset();p={};
  if(!d.available){assert(ends(command(p,std::string("v1 x check ")+d.key),"denied wrong_expansion"));continue;}
  assert(FindDestination(d.key,false)==&d);
  std::istringstream aliases(d.aliases);for(std::string alias;aliases>>alias;){
   reset();p={};for(char& c:alias)if(c>='a'&&c<='z')c-='a'-'A';
   assert(FindDestination(alias,true)==&d);command(p,alias);assert(p.teleports==1&&p.mapId==d.map&&p.x==d.x&&p.y==d.y&&p.z==d.z);
   assert((p.lastEntry!=nullptr)==(d.map==d.instanceMap));
  }
  reset();p={};assert(ends(command(p,std::string("v1 x check ")+d.key),"ready ok"));
  assert(ends(command(p,std::string("v1 x go ")+d.key),"pending transfer"));
  assert(ends(command(p,std::string("v1 x status ")+d.key),"pending transfer"));
  arrive(p);assert(ends(command(p,std::string("v1 x status ")+d.key),"arrived ok"));
  p.x+=21;assert(ends(command(p,std::string("v1 x status ")+d.key),"denied moved_away"));
 }
 // Independent human safety flags must survive refusal, without invoking TeleportTo.
 const std::vector<std::pair<bool Player::*,std::string>> guards={
  {&Player::combat,"combat"},{&Player::taxi,"taxi"},{&Player::transport,"transport"},{&Player::arena,"arena"},
  {&Player::bg,"battleground"},{&Player::charm,"controlled"},{&Player::rooted,"controlled"},
  {&Player::controlled,"controlled"},{&Player::gm,"gm_mode"},{&Player::transfer,"transfer_busy"}};
 for(auto const& flag:guards){if(Expansion==0&&flag.second=="arena")continue;reset();p={};p.*flag.first=true;assert(ends(command(p,"v1 x check deadmines"),"denied "+flag.second));assert(!p.teleports&&p.*flag.first);}
 reset();p={};p.alive=false;assert(ends(command(p,"v1 x check deadmines"),"denied dead"));assert(!p.alive);
 reset();p={};p.real=false;assert(ends(command(p,"v1 x check deadmines"),"denied not_player"));
 reset();p={};p.map.dungeon=true;assert(ends(command(p,"v1 x check deadmines"),"denied instance"));
 reset();p={};sConfig.enabled=false;assert(ends(command(p,"v1 x check deadmines"),"denied disabled"));
 reset();p={};Group group;Player other;other.id=2;p.group=other.group=&group;
 command(p,"v1 x check deadmines");group.leader=2;assert(ends(command(p,"v1 x go deadmines"),"denied not_leader"));assert(!p.teleports&&!other.teleports);
 reset();p={};p.group=&group;group.leader=1;command(p,"v1 x check deadmines");command(p,"v1 x go deadmines");
 assert(p.teleports==1&&!other.teleports&&group.leader==1&&other.group==&group);
 reset();p={};const auto* rfc=FindDestination("ragefire_chasm",false);assert(rfc);sObjectMgr.entries[rfc->entryTrigger].requiredLevel=8;p.level=7;
 assert(ends(command(p,"v1 x check ragefire_chasm"),"denied too_low_level"));
 for(auto lock:{AREA_LOCKSTATUS_RAID_LOCKED,AREA_LOCKSTATUS_ZONE_IN_COMBAT,AREA_LOCKSTATUS_INSTANCE_IS_FULL,AREA_LOCKSTATUS_HAS_BIND,AREA_LOCKSTATUS_OTHER}){
  reset();p={};command(p,"v1 x check ragefire_chasm");p.lock=lock;auto result=command(p,"v1 x go ragefire_chasm");
  assert(result.find("denied")!=std::string::npos&&!p.teleports&&p.lockChecks==2);
 }
 if(Expansion==2){reset();p={};sOutdoorPvPMgr.battlefield.team=1;assert(ends(command(p,"v1 x check vault_archavon"),"denied not_owner"));
  reset();p={};command(p,"v1 x check vault_archavon");sOutdoorPvPMgr.battlefield.status=BF_STATUS_IN_PROGRESS;
  assert(ends(command(p,"v1 x go vault_archavon"),"denied battle_in_progress"));assert(!p.teleports);}
 reset();p={};for(int n=0;n<6;++n)command(p,"v1 x check deadmines");assert(ends(command(p,"v1 x status deadmines"),"denied rate_limit"));
 fakeNow+=2;assert(ends(command(p,"v1 x check deadmines"),"ready ok"));
 // Service owner isolation, bounded receipts, expiry, cleanup, and exact 20-yard boundary.
 Service s;Service::Owner owner{1,1},otherOwner{2,1};assert(s.AllowRequest(owner,100));assert(s.AllowRequest(otherOwner,100));
 Position pos;Destination d{"test","test","",0,2,true,1,1,1,1,2,3,0};unsigned calls=0;
 auto process=[&](Service::Owner who,std::string id,std::string op,uint64_t now){return s.Process(who,id,op,"test",&d,Expansion,pos,"",0,now,[&](){++calls;return true;});};
 assert(process(owner,"a","check",100).state=="ready");assert(process(otherOwner,"a","go",100).reason=="expired");
 assert(process(owner,"a","go",100).state=="pending");assert(calls==1);assert(process(owner,"a","go",101).state=="pending"&&calls==1);
 assert(process(owner,"a","status",160).reason=="expired");assert(process(owner,"a","go",160).reason=="expired"&&calls==1);
 for(unsigned i=0;i<Service::MaxReceipts-1;++i)assert(process(owner,"id"+std::to_string(i),"check",160).state=="ready");
 assert(process(owner,"full","check",160).reason=="busy");s.AllowRequest({3,3},1000);assert(s.OwnerCount()==1);
 pos.inWorld=pos.alive=true;pos.transferring=false;pos.map=1;pos.x=21;pos.y=2;pos.z=3;assert(pos.At(d));pos.x+=0.01f;assert(!pos.At(d));
 Service capped;for(unsigned i=0;i<Service::MaxOwners;++i)assert(capped.AllowRequest({i,i},100));assert(!capped.AllowRequest({99999,99999},100));

 // Persistent first-entry unlocks: no history means locked and no teleport.
 reset();p={};CharacterDatabase.persisted.clear();
 assert(ends(command(p,"v1 locked check deadmines"),"denied undiscovered"));assert(!p.teleports);
 command(p,"deadmines");assert(ends(messages.back(),"unlock its teleport for this account."));assert(!p.teleports);
 reset();p={};CharacterDatabase.persisted.clear();
 const auto* dungeon=FindDestination("ragefire_chasm",false);assert(dungeon);
 p.mapId=dungeon->instanceMap;p.map.dungeon=true;p.RecordDungeonTravelVisit();
 assert(CharacterDatabase.persisted[1].count("ragefire_chasm")==1&&CharacterDatabase.writes==1);
 assert(p.HasDungeonTravelUnlock("ragefire_chasm"));p.RecordDungeonTravelVisit();assert(CharacterDatabase.writes==1);
 // A fresh Player object models a relog/restart; only the database survives.
 p={};assert(p.LoadDungeonTravelUnlocks()&&p.HasDungeonTravelUnlock("ragefire_chasm"));
 assert(!p.HasDungeonTravelUnlock("deadmines"));
 assert(ends(command(p,"v1 learned check ragefire_chasm"),"ready ok"));assert(!p.teleports);
 Player otherCharacter;otherCharacter.id=2;assert(otherCharacter.LoadDungeonTravelUnlocks()&&otherCharacter.HasDungeonTravelUnlock("ragefire_chasm"));
 // A failed write cannot create a transient free unlock; entering again can retry.
 reset();p={};CharacterDatabase.persisted.clear();CharacterDatabase.writeOK=false;p.mapId=389;p.map.dungeon=true;p.RecordDungeonTravelVisit();
 assert(!p.HasDungeonTravelUnlock("ragefire_chasm")&&CharacterDatabase.persisted[1].empty());
 CharacterDatabase.writeOK=true;p.RecordDungeonTravelVisit();assert(p.HasDungeonTravelUnlock("ragefire_chasm"));
 reset();p={};CharacterDatabase.readOK=false;assert(ends(command(p,"v1 x check deadmines"),"denied storage_unavailable"));assert(!p.teleports);
 // No unlock for outdoor proximity, incomplete entry, death, GM mode or bots.
 for(unsigned flag=0;flag<5;++flag){reset();p={};CharacterDatabase.persisted.clear();p.mapId=389;p.map.dungeon=true;
  if(flag==0)p.map.dungeon=false;if(flag==1)p.world=false;if(flag==2)p.alive=false;if(flag==3)p.gm=true;if(flag==4)p.real=false;
  p.RecordDungeonTravelVisit();assert(!CharacterDatabase.reads&&!CharacterDatabase.writes&&CharacterDatabase.persisted.empty());}
 reset();p={};CharacterDatabase.persisted.clear();p.mapId=189;p.map.dungeon=true;p.RecordDungeonTravelVisit();
 for(auto key:{"scarlet_graveyard","scarlet_library","scarlet_armory","scarlet_cathedral"})assert(p.HasDungeonTravelUnlock(key));
 assert(CharacterDatabase.writes==1); // Shared-map wings saved atomically.
 reset();p={};CharacterDatabase.persisted.clear();p.mapId=533;p.map.dungeon=true;p.RecordDungeonTravelVisit();
 assert(p.HasDungeonTravelUnlock(Expansion==2?"naxxramas":"naxxramas_40"));
 assert(!p.HasDungeonTravelUnlock(Expansion==2?"naxxramas_40":"naxxramas"));
 // Read-only bounded catalog works independently of current combat/instance eligibility.
 reset();p={};CharacterDatabase.persisted.clear();CharacterDatabase.persisted[1].insert("deadmines");p.combat=true;p.map.dungeon=true;
 command(p,"v1 catalog unlocks all");unsigned expected=Expansion==0?32:Expansion==1?57:80;
 assert(messages.front()=="PBTPU 1 catalog begin "+std::to_string(expected));assert(messages.size()==expected+2);
 assert(messages.back()=="PBTPU 1 catalog end "+std::to_string(expected));
 assert(std::find(messages.begin(),messages.end(),"PBTPU 1 catalog deadmines unlocked")!=messages.end());
 assert(std::find(messages.begin(),messages.end(),"PBTPU 1 catalog uldaman locked")!=messages.end());assert(!p.teleports&&!CharacterDatabase.writes);
 assert(ends(command(p,"v1 catalog2 unlocks all"),"denied rate_limit"));fakeNow+=10;
 assert(ends(command(p,"v1 catalog3 unlocks all"),"end "+std::to_string(expected)));
 reset();p={};CharacterDatabase.readOK=false;assert(ends(command(p,"v1 bad unlocks all"),"denied storage_unavailable"));

 // Authoritative read-only cooldown snapshots, independent of teleport eligibility.
 reset();p={};CharacterDatabase.readOK=false;p.combat=true;p.gm=true;p.alive=false;
 assert(command(p,"v1 initial cooldown self")=="PBTPC 1 initial 0 300");
 assert(!p.teleports&&!CharacterDatabase.reads&&!CharacterDatabase.writes);
 assert(command(p,"v1 fast cooldown self")=="PBTP 1 fast self denied rate_limit");
 fakeNow+=10;assert(command(p,"v1 later cooldown self")=="PBTPC 1 later 0 300");
 // Reading creates no travel receipt, unlock or permission to use go.
 p={};assert(command(p,"v1 later go deadmines")=="PBTP 1 later deadmines denied expired");
 reset();p={};command(p,"v1 trip check deadmines");command(p,"v1 trip go deadmines");
 assert(command(p,"v1 first cooldown self")=="PBTPC 1 first 300 300");
 assert(p.teleports==1);
 fakeNow+=10;assert(command(p,"v1 second cooldown self")=="PBTPC 1 second 290 300");
 // Replayed go and reads cannot renew or consume the travel cooldown.
 command(p,"v1 trip go deadmines");
 for(unsigned step=2;step<=30;++step){fakeNow=100+step*10;
  assert(command(p,"v1 tick cooldown self")=="PBTPC 1 tick "+std::to_string(300-step*10)+" 300");}
 assert(p.teleports==1);arrive(p);
 assert(ends(command(p,"v1 after check uldaman"),"ready ok"));
 // Manual travel shares the same authoritative timer. Relog replaces Player/Session only.
 reset();p={};command(p,"deadmines");assert(p.teleports==1);fakeNow+=17;p={};
 assert(command(p,"v1 reconnect cooldown self")=="PBTPC 1 reconnect 283 300");
 Player alternate;alternate.id=2;
 assert(command(alternate,"v1 otherchar cooldown self")=="PBTPC 1 otherchar 0 300");
 assert(command(p,"v1 otheraccount cooldown self",2)=="PBTPC 1 otheraccount 0 300");
 // Existing cooldown state is in memory: a restarted Service has no previous timer.
 travel=Service{};
 assert(command(p,"v1 restarted cooldown self")=="PBTPC 1 restarted 0 300");
 // Supported configuration bounds and one-second resolution match enforcement.
 for(int value:{-1,0,17,300,3600,3601,2147483647}){
  reset();p={};sConfig.cooldown=value;command(p,"deadmines");
  unsigned duration=static_cast<unsigned>(std::min(3600,std::max(0,value)));
  assert(command(p,"v1 duration cooldown self")=="PBTPC 1 duration "+std::to_string(duration)+" "+std::to_string(duration));
  assert(travel.RemainingCooldown({1,1},101)==(duration?duration-1:0));
  assert(travel.RemainingCooldown({1,1},100+duration)==0);
 }
 // Reloading the configured duration does not rewrite an already running timer.
 reset();p={};command(p,"deadmines");sConfig.cooldown=17;fakeNow+=10;
 assert(command(p,"v1 changed cooldown self")=="PBTPC 1 changed 290 17");
 fakeNow+=10;sConfig.cooldown=0;
 assert(command(p,"v1 disabledtimer cooldown self")=="PBTPC 1 disabledtimer 280 0");
 // Refused travel or failed native initiation does not start cooldown.
 reset();p={};p.combat=true;command(p,"deadmines");
 assert(command(p,"v1 refused cooldown self")=="PBTPC 1 refused 0 300");
 reset();p={};p.nativeSuccess=false;command(p,"deadmines");
 assert(command(p,"v1 failed cooldown self")=="PBTPC 1 failed 0 300");
 // Snapshot throttling is independent of unlock-catalog throttling and destination receipts.
 reset();p={};command(p,"v1 list unlocks all");
 assert(command(p,"v1 timer cooldown self")=="PBTPC 1 timer 0 300");
 assert(ends(command(p,"v1 trip check deadmines"),"ready ok"));
 assert(ends(command(p,"v1 trip go deadmines"),"pending transfer"));
 fakeNow+=10;assert(command(p,"v1 timer2 cooldown self")=="PBTPC 1 timer2 290 300");
 // Malformed requests never accept another character target or unsafe request IDs.
 for(std::string request:std::vector<std::string>{"v1 bad/id cooldown self","v1 id cooldown 2","v1 id cooldown","v1 id cooldown self extra",
                         "v1 "+std::string(65,'a')+" cooldown self"}){
  reset();p={};auto line=command(p,request);
  assert(ends(line,"self denied arguments"));assert(line.find("bad/id")==std::string::npos);
  assert(!p.teleports&&!CharacterDatabase.reads&&!CharacterDatabase.writes);
 }
 reset();p={};std::string longest(64,'a');
 assert(command(p,"v1 "+longest+" cooldown self")=="PBTPC 1 "+longest+" 0 300");
 reset();p={};sConfig.enabled=false;
 assert(command(p,"v1 off cooldown self")=="PBTP 1 off self denied disabled");
 reset();p={};for(unsigned i=0;i<6;++i)command(p,"v1 x check deadmines");
 assert(command(p,"v1 overloaded cooldown self")=="PBTP 1 overloaded self denied rate_limit");
 // Reads cannot extend transaction expiry or retained receipt lifetime.
 reset();p={};command(p,"v1 expires check deadmines");
 for(unsigned tick=0;tick<=6;++tick){fakeNow=100+tick*10;command(p,"v1 snapshot cooldown self");}
 assert(command(p,"v1 expires go deadmines")=="PBTP 1 expires deadmines denied expired");assert(!p.teleports);
 fakeNow=461;command(p,"v1 cleanup cooldown self");
 assert(ends(command(p,"v1 expires check deadmines"),"ready ok"));

 // Already-connected alts see new account discovery at their next request.
 reset();p={};CharacterDatabase.persisted.clear();Player alt;alt.id=2;
 assert(alt.LoadDungeonTravelUnlocks()&&!alt.HasDungeonTravelUnlock("ragefire_chasm"));
 p.mapId=389;p.map.dungeon=true;p.RecordDungeonTravelVisit();
 assert(alt.LoadDungeonTravelUnlocks()&&alt.HasDungeonTravelUnlock("ragefire_chasm"));
 assert(ends(command(alt,"v1 shared check ragefire_chasm"),"ready ok"));
 assert(ends(command(alt,"v1 shared go ragefire_chasm"),"pending transfer"));
 // Account discovery is shared but cooldown and receipts are still per character.
 p={};assert(command(p,"v1 mainTimer cooldown self")=="PBTPC 1 mainTimer 0 300");
 assert(command(alt,"v1 altTimer cooldown self")=="PBTPC 1 altTimer 300 300");
 Player stranger;stranger.id=3;stranger.session.account=2;
 assert(stranger.LoadDungeonTravelUnlocks()&&!stranger.HasDungeonTravelUnlock("ragefire_chasm"));
 assert(ends(command(stranger,"v1 private check ragefire_chasm",2),"denied undiscovered"));
 // A database failure cannot use a stale prior account snapshot to grant a port.
 p.LoadDungeonTravelUnlocks();CharacterDatabase.readOK=false;
 assert(ends(command(p,"v1 stale check ragefire_chasm"),"denied storage_unavailable"));assert(!p.teleports);
 // Legacy rows written during the upgrade window remain visible, without a read granting new discovery.
 reset();p={};CharacterDatabase.persisted.clear();CharacterDatabase.legacy[1].insert("deadmines");
 assert(p.LoadDungeonTravelUnlocks()&&p.HasDungeonTravelUnlock("deadmines"));
 assert(!CharacterDatabase.writes&&CharacterDatabase.persisted[1].empty());
 CharacterDatabase.legacy[1].insert("uldaman");
 assert(p.LoadDungeonTravelUnlocks()&&p.HasDungeonTravelUnlock("uldaman"));
 reset();p={};p.session.account=0;assert(!p.LoadDungeonTravelUnlocks()&&!CharacterDatabase.reads);

 std::cout<<"PASS: account discovery and refreshed alt snapshots; cooldown snapshot protocol and isolation; expansion "<<Expansion<<", persistent first-entry unlocks and catalog; complete alias inventory; actual adapter/parser and service guards, native-entry handoff, single-player movement, arrival/replay/expiry/cooldown/rate limits. Controlled APIs; not live travel.\n";
}
'''
with tempfile.TemporaryDirectory(prefix='player-travel-test-') as directory:
    folder=Path(directory);cpp=folder/'test.cpp';exe=folder/('test.exe' if os.name=='nt' else 'test')
    cpp.write_text(stubs+'\n'+source+'\n'+tests)
    includes=str(root/'src/game/Chat')
    if os.name=='nt':
        args=['cl','/nologo','/EHsc','/std:c++17','/DENABLE_PLAYERBOTS','/I'+includes,str(cpp),'/Fe:'+str(exe),'/Fo:'+str(folder/'test.obj')]
    else:args=['c++','-std=c++17','-DENABLE_PLAYERBOTS','-I'+includes,str(cpp),'-o',str(exe)]
    subprocess.run(args,check=True,cwd=folder)
    subprocess.run([str(exe)],check=True,cwd=folder)
