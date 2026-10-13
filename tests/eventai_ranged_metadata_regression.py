from pathlib import Path
import sys,subprocess,tempfile,shutil
root=Path(sys.argv[1]);s=(root/'src/game/AI/EventAI/CreatureEventAI.cpp').read_text()
mark='void CreatureEventAI::SpellListChanged()';start=s.index(mark);o=s.index('{',start);depth=0
for end in range(o,len(s)):
 depth+=(s[end]=='{')-(s[end]=='}')
 if not depth:break
method=s[start:end+1]
code=r"""#include <cassert>
#include <vector>
#include <set>
#include <iostream>
using uint32=unsigned;enum{MAX_ACTIONS=3,ACTION_T_CAST=11,CAST_MAIN_SPELL=256,CAST_DISTANCE_YOURSELF=512};
struct Action{unsigned type=0;struct Cast{unsigned spellId=0,castFlags=0;}cast;};
struct Holder{struct Event{Action action[MAX_ACTIONS];}event;};
struct CreatureAI{unsigned main=0,listMain=0;std::set<unsigned>allMain,distance;virtual ~CreatureAI()=default;virtual void SpellListChanged(){main=listMain;allMain.clear();if(listMain)allMain.insert(listMain);}void AddMainSpell(unsigned id){if(!main)main=id;allMain.insert(id);}void AddDistanceSpell(unsigned id){distance.insert(id);}};
struct CreatureEventAI:CreatureAI{std::vector<Holder>m_CreatureEventAIList;void SpellListChanged()override;};
"""+method+r"""
int main(){CreatureEventAI ai;Holder event;event.event.action[1].type=ACTION_T_CAST;event.event.action[1].cast={6660,CAST_MAIN_SPELL};event.event.action[2].type=ACTION_T_CAST;event.event.action[2].cast={100,CAST_DISTANCE_YOURSELF};ai.m_CreatureEventAIList.push_back(event);
 ai.AddMainSpell(6660);CreatureAI*owner=&ai;owner->SpellListChanged();assert(ai.main==6660&&ai.allMain.count(6660)&&ai.distance.count(100));
 // Native list primary takes precedence; legacy metadata still stays admitted.
 ai.listMain=42;owner->SpellListChanged();assert(ai.main==42&&ai.allMain.count(42)&&ai.allMain.count(6660));
 ai.m_CreatureEventAIList.clear();owner->SpellListChanged();assert(ai.main==42&&!ai.allMain.count(6660));
 ai.listMain=0;owner->SpellListChanged();assert(ai.main==0&&ai.allMain.empty());
 std::cout<<"PASS native EventAI spell-list callback: main cast survives, base primary priority retained, no stale event definitions\n";}
"""
with tempfile.TemporaryDirectory(prefix='eventai-ranged-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(code);compiler='cl' if shutil.which('cl') else 'c++';args=[compiler,'/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'] if compiler=='cl' else [compiler,'-std=c++17','test.cpp','-o','test'];subprocess.run(args,cwd=p,check=True);subprocess.run([str(p/('test.exe' if compiler=='cl' else 'test'))],cwd=p,check=True)
