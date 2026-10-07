"""Compile production event-lookup bodies; optionally time an exported spawn/event fixture."""
from pathlib import Path
import subprocess,tempfile,sys
root=Path(__file__).resolve().parents[2]
def method(path,signature):
 s=(root/path).read_text();a=s.index(signature);b=s.index('{',a);d=1;i=b+1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
code=r"""
#include <cassert>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <list>
#include <sstream>
#include <unordered_map>
#include <vector>
using uint32=uint32_t;using int32=int32_t;using int16=int16_t;using uint16=uint16_t;
struct Creature{};struct GameObject{};struct Pool{};
struct GameEventMgr {
 std::vector<int> m_gameEvents;
 std::vector<std::list<uint32>> m_gameEventCreatureGuids,m_gameEventGameobjectGuids;
 std::vector<std::list<uint16>> m_gameEventSpawnPoolIds;
 std::unordered_map<uint32,int16> m_creatureEventLookup,m_gameObjectEventLookup,m_poolEventLookup;
 void RebuildEventLookup();template<class T>int16 GetGameEventId(uint32);
};
template<class Groups>int16 legacy(Groups const& groups,uint32 guid,int offset) {
 for(size_t i=0;i<groups.size();++i)for(auto candidate:groups[i])if(candidate==guid)return int16(int(i)+offset);
 return 0;
}
"""
src='src/game/GameEvents/GameEventMgr.cpp'
code+=method(src,'void GameEventMgr::RebuildEventLookup()')+'\n'
for kind in ('Creature','GameObject','Pool'):
 code+='template<>\n'+method(src,f'int16 GameEventMgr::GetGameEventId<{kind}>(uint32 guid_or_poolid)')+'\n'
code+=r"""
int main(int argc,char** argv){
 GameEventMgr m;m.m_gameEvents.resize(5);m.m_gameEventCreatureGuids.resize(9);m.m_gameEventGameobjectGuids.resize(9);m.m_gameEventSpawnPoolIds.resize(5);
 m.m_gameEventCreatureGuids[1]={7,8};m.m_gameEventCreatureGuids[6]={7,10};m.m_gameEventGameobjectGuids[2]={7,11};m.m_gameEventGameobjectGuids[8]={11,12};m.m_gameEventSpawnPoolIds[2]={4,5};m.m_gameEventSpawnPoolIds[3]={4};m.RebuildEventLookup();
 for(uint32 guid=0;guid<20;++guid){
 assert(m.GetGameEventId<Creature>(guid)==legacy(m.m_gameEventCreatureGuids,guid,-4));
 assert(m.GetGameEventId<GameObject>(guid)==legacy(m.m_gameEventGameobjectGuids,guid,-4));
 assert(m.GetGameEventId<Pool>(guid)==legacy(m.m_gameEventSpawnPoolIds,guid,0));}
 m.m_gameEventCreatureGuids[1].clear();m.RebuildEventLookup();assert(m.GetGameEventId<Creature>(8)==0);assert(m.GetGameEventId<Creature>(7)==2);
 m.m_gameEvents.clear();m.m_gameEventCreatureGuids.clear();m.m_gameEventGameobjectGuids.clear();m.m_gameEventSpawnPoolIds.clear();m.RebuildEventLookup();assert(m.GetGameEventId<Creature>(7)==0);
 if(argc>1){
  std::ifstream f(argv[1]);assert(f);std::string line;std::vector<std::tuple<char,uint32,int>> rows;uint32 maxEvent=0;
  while(std::getline(f,line)){std::istringstream in(line);char kind;uint32 guid;int event;if(!(in>>kind>>guid>>event))continue;rows.emplace_back(kind,guid,event);if(kind=='M')maxEvent=guid;}
  assert(maxEvent);m.m_gameEvents.resize(maxEvent+1);m.m_gameEventCreatureGuids.resize(2*maxEvent+1);m.m_gameEventGameobjectGuids.resize(2*maxEvent+1);
  std::vector<uint32> c,g;
  for(auto [kind,guid,event]:rows){if(kind=='C')c.push_back(guid);if(kind=='G')g.push_back(guid);if(kind=='E')m.m_gameEventCreatureGuids.at(event+maxEvent).push_back(guid);if(kind=='O')m.m_gameEventGameobjectGuids.at(event+maxEvent).push_back(guid);}
  std::vector<int16> expected;expected.reserve(c.size()+g.size());auto before=std::chrono::steady_clock::now();
  for(auto guid:c)expected.push_back(legacy(m.m_gameEventCreatureGuids,guid,-int(maxEvent)));
  for(auto guid:g)expected.push_back(legacy(m.m_gameEventGameobjectGuids,guid,-int(maxEvent)));
  auto mid=std::chrono::steady_clock::now();m.RebuildEventLookup();size_t n=0;
  for(auto guid:c)assert(expected[n++]==m.GetGameEventId<Creature>(guid));
  for(auto guid:g)assert(expected[n++]==m.GetGameEventId<GameObject>(guid));
  auto end=std::chrono::steady_clock::now();std::cout<<"lookups="<<n<<" legacy_seconds="<<std::chrono::duration<double>(mid-before).count()<<" indexed_build_and_lookup_seconds="<<std::chrono::duration<double>(end-mid).count()<<" identical_results=1\n";
 }
}
"""
with tempfile.TemporaryDirectory(prefix='event-lookup-regression-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(code)
 c=subprocess.run(['cl','/nologo','/std:c++20','/O2','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if c.returncode:raise RuntimeError(c.stdout+c.stderr)
 subprocess.run([str(p/'test.exe'),*sys.argv[1:]],cwd=p,check=True)
print(root.name+': event lookup preserves signed IDs, first-match order, missing entries and rebuilds')
