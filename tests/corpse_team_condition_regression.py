from pathlib import Path
import re,subprocess,sys,tempfile,shutil
root=Path(sys.argv[1]);s=(root/'src/game/Globals/Conditions.cpp').read_text();h=(root/'src/game/Globals/Conditions.h').read_text()
def block(text,mark):
 start=text.index(mark);o=text.index('{',start);depth=0
 for end in range(o,len(text)):
  depth+=(text[end]=='{')-(text[end]=='}')
  if not depth:return text[start:end+1]
 raise AssertionError(mark)
req=block(h,'enum ConditionRequirement')+';'
array=block(s,'uint8 const ConditionTargetsInternal[]')+';'
check=block(s,'bool ConditionEntry::CheckParamRequirements')
meets=block(s,'bool ConditionEntry::Meets(')
team=block(s,'case CONDITION_TEAM:');team=team[team.index('{')+1:-1]
code=r"""#include <cassert>
#include <cstdint>
#include <utility>
#include <iostream>
using uint8=std::uint8_t;using uint32=std::uint32_t;
#define DEBUG_LOG(...) ((void)0)
enum {CONDITION_FROM_REFERING_LOOT=1,CONFIG_BOOL_ALLOW_TWO_SIDE_INTERACTION_AUCTION=1,CONDITION_FLAG_SWAP_TARGETS=2,CONDITION_FLAG_REVERSE_RESULT=1};using ConditionSource=int;
struct World{bool allow=false;bool getConfig(int){return allow;}}sWorld;
struct Log{int errors=0;void outErrorDb(const char*,...){++errors;}}sLog;
const char*conditionSourceToStr[]={"loot","reference"};
struct Guid{const char*c_str()const{return "test";}};
struct Map{int GetId()const{return 0;}};
struct WorldObject{int kind=0;bool IsPlayer()const{return kind==1;}bool IsCorpse()const{return kind==2;}bool IsUnit()const{return kind==1||kind==3;}bool IsCreature()const{return kind==3;}bool IsGameObject()const{return kind==4;}Guid GetGuidStr()const{return {};}};
struct Player:WorldObject{uint32 team;Player(uint32 t):team(t){kind=1;}uint32 GetTeam()const{return team;}};
struct Corpse:WorldObject{uint32 team;Corpse(uint32 t):team(t){kind=2;}uint32 GetTeam()const{return team;}};
struct ConditionEntry{uint32 m_entry=3021,m_condition=6,m_flags=0,m_value1=67;bool CheckParamRequirements(WorldObject const*,Map const*,WorldObject const*)const;bool Meets(WorldObject const*,Map const*,WorldObject const*,ConditionSource)const;bool Evaluate(WorldObject const*target,Map const*map,WorldObject const*source,ConditionSource conditionSourceType)const{
"""+team+'}};\n'+req+'\n'+array+'\nuint8 const*ConditionTargets=&ConditionTargetsInternal[3];\n'+check+'\n'+meets+r"""
int main(){ConditionEntry c;Player horde(67),alliance(469);Corpse hc(67),ac(469);WorldObject creature;creature.kind=3;Map m;
 assert(c.Meets(&horde,&m,nullptr,0));assert(!c.Meets(&alliance,&m,nullptr,0));
 assert(c.Meets(&hc,&m,nullptr,0));assert(!c.Meets(&ac,&m,nullptr,0));
 assert(!c.Meets(&creature,&m,nullptr,0));assert(!c.Meets(nullptr,&m,nullptr,0));
 c.m_flags=CONDITION_FLAG_SWAP_TARGETS;assert(c.Meets(&alliance,&m,&hc,0));assert(!c.Meets(&horde,&m,&ac,0));
 c.m_flags|=CONDITION_FLAG_REVERSE_RESULT;assert(c.Meets(&horde,&m,&ac,0));
 sWorld.allow=true;c.m_flags=0;assert(c.Meets(&ac,&m,nullptr,CONDITION_FROM_REFERING_LOOT));
 assert(sLog.errors==2);std::cout<<"PASS native team condition: player/corpse teams, swap, reverse, bad targets, auction override\n";}
"""
with tempfile.TemporaryDirectory(prefix='corpse-team-regression-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(code);compiler='cl' if shutil.which('cl') else 'c++'
 args=[compiler,'/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'] if compiler=='cl' else [compiler,'-std=c++17','test.cpp','-o','test']
 subprocess.run(args,cwd=p,check=True);subprocess.run([str(p/('test.exe' if compiler=='cl' else 'test'))],cwd=p,check=True)
