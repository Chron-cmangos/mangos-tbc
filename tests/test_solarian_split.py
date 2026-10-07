"""Execute the native split callbacks against failed/despawned portal fixtures."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
relative = 'src/game/AI/ScriptDevAI/scripts/outland/tempest_keep/the_eye/boss_astromancer.cpp'
source = (root / relative).read_text()

def block(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == '{': depth += 1
        elif text[index] == '}':
            depth -= 1
            if not depth: return text[start:index + 1]
    raise AssertionError(marker)

methods = '\n'.join(block(source, marker) for marker in (
    'void Reset() override', 'bool ValidateSplitSpotlights()',
    'void HandleSplitAgents()', 'void HandleSplitPriests()'))
code = r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>
#include <vector>
using uint8=unsigned char;using uint32=unsigned;using ObjectGuid=unsigned;
enum { PHASE_NORMAL=1,PHASE_SPLIT=2,PHASE_VOID=3,MAX_SPOTLIGHTS=3,
 NPC_ASTROMANCER_SOLARIAN_SPOTLIGHT=18928,SPELL_ASTROMANCER_ADDS=33362,
 SPELL_ASTROMANCER_PRIEST=33367,TRIGGERED_OLD_TRIGGERED=1,VISIBILITY_OFF=0,VISIBILITY_ON=1,
 SOLARIAN_SPLIT_PRIESTS=8,SOLARIAN_ARCANE_MISSILES,SOLARIAN_BLINDING_LIGHT,
 SOLARIAN_WRATH_OF_THE_ASTROMANCER,SOLARIAN_SPLIT_PHASE };
struct GuidVector:std::vector<ObjectGuid>{using std::vector<ObjectGuid>::vector;
 using std::vector<ObjectGuid>::operator=;
 ObjectGuid operator[](size_t index)const{return at(index);} }; // trap unchecked old indexing deterministically
struct Map;
struct Creature{Map* map=nullptr;unsigned entry=18928,guid=1,visibility=0,armor=0;
 bool alive=true,world=true,combat=true;unsigned agents=0,priests=0,ports=0;
 bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsInCombat(){return combat;}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}Map* GetMap(){return map;}
 void CastSpell(void*,unsigned spell,unsigned,void*,void*,ObjectGuid owner){assert(owner==99);
 if(spell==SPELL_ASTROMANCER_ADDS)++agents;else {assert(spell==SPELL_ASTROMANCER_PRIEST);++priests;}}
 float GetPositionX(){return float(guid);}float GetPositionY(){return 2;}float GetPositionZ(){return 3;}
 float GetOrientation(){return 4;}void NearTeleportTo(float,float,float,float,bool){++ports;}
 void SetArmor(unsigned value){armor=value;}unsigned GetVisibility(){return visibility;}
 void SetVisibility(unsigned value){visibility=value;}};
struct Map{std::map<ObjectGuid,Creature*> creatures;Creature* GetCreature(ObjectGuid guid){
 auto i=creatures.find(guid);return i==creatures.end()?nullptr:i->second;}};
struct Logger{unsigned errors=0;void outError(const char*){++errors;}}sLog;
std::mt19937 randomGenerator(7);std::mt19937* GetRandomGenerator(){return &randomGenerator;}
unsigned urand(unsigned a,unsigned){return a;}
struct CombatAI{virtual void Reset(){}};
struct AI:CombatAI{Creature* m_creature;unsigned m_Phase=PHASE_SPLIT,m_uiDefaultArmor=125;
 GuidVector m_vSpotLightsGuidVector;unsigned evades=0;bool moving=false,scripted=true,melee=false;
 std::map<unsigned,unsigned> timers,combatTimers;
 AI(Creature* boss):m_creature(boss){}
 void SetCombatMovement(bool value,bool=false){moving=value;}
 void SetCombatScriptStatus(bool value){scripted=value;}void SetMeleeEnabled(bool value){melee=value;}
 void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}
 void ResetCombatAction(unsigned id,unsigned delay){combatTimers[id]=delay;}
 void EnterEvadeMode(){++evades;m_creature->combat=false;timers.clear();combatTimers.clear();Reset();}
 __METHODS__
};
int main(){
 for(unsigned count:{0u,1u,2u,4u}){Map map;Creature boss;boss.map=&map;boss.guid=99;
 AI ai(&boss);for(unsigned i=0;i<count;++i)ai.m_vSpotLightsGuidVector.push_back(i+1);
 unsigned errors=sLog.errors;ai.HandleSplitAgents();assert(ai.evades==1&&sLog.errors==errors+1);
 assert(ai.timers.empty()&&ai.combatTimers.empty()&&ai.m_vSpotLightsGuidVector.empty());
 assert(ai.m_Phase==PHASE_NORMAL&&ai.melee&&ai.moving&&!ai.scripted&&boss.visibility==VISIBILITY_ON);
 ai.HandleSplitPriests();assert(ai.evades==1&&boss.ports==0);}
 for(unsigned defect=0;defect<6;++defect){Map map;Creature boss,p1,p2,p3;
 boss.map=&map;boss.guid=99;p1.guid=1;p2.guid=2;p3.guid=3;map.creatures={{1,&p1},{2,&p2},{3,&p3}};
 AI ai(&boss);ai.m_vSpotLightsGuidVector={1,2,3};
 if(defect==0)map.creatures.erase(3);if(defect==1)p2.alive=false;if(defect==2)p2.world=false;
 if(defect==3)p2.entry=123;if(defect==4)ai.m_vSpotLightsGuidVector={1,1,3};
 if(defect==5){ai.HandleSplitAgents();assert(p1.agents+p2.agents+p3.agents==3);map.creatures.erase(2);}
 ai.HandleSplitPriests();assert(ai.evades==1&&boss.ports==0&&p1.priests+p2.priests+p3.priests==0);}
 {Map map;Creature boss,p1,p2,p3;boss.map=&map;boss.guid=99;p1.guid=1;p2.guid=2;p3.guid=3;
 map.creatures={{1,&p1},{2,&p2},{3,&p3}};AI ai(&boss);ai.m_vSpotLightsGuidVector={1,2,3};
 ai.HandleSplitAgents();assert(ai.evades==0&&p1.agents==1&&p2.agents==1&&p3.agents==1);
 assert(ai.timers.at(SOLARIAN_SPLIT_PRIESTS)==16000);
 ai.HandleSplitPriests();assert(ai.evades==0&&p1.priests+p2.priests+p3.priests==2&&boss.ports==1);
 assert(ai.m_Phase==PHASE_NORMAL&&ai.melee&&ai.moving&&!ai.scripted&&boss.visibility==VISIBILITY_ON);
 assert(ai.combatTimers.at(SOLARIAN_SPLIT_PHASE)==70000);}
 for(unsigned stale=0;stale<3;++stale){Map map;Creature boss;boss.map=&map;AI ai(&boss);
 if(stale==0)ai.m_Phase=PHASE_NORMAL;if(stale==1)boss.alive=false;if(stale==2)boss.combat=false;
 unsigned errors=sLog.errors;ai.HandleSplitAgents();ai.HandleSplitPriests();
 assert(ai.evades==0&&sLog.errors==errors&&ai.timers.empty()&&ai.combatTimers.empty());}
 std::cout<<"PASS: native Solarian failed/despawned/duplicate spotlights, phase cleanup and unchanged valid split\n";
}
'''.replace('__METHODS__', methods)
with tempfile.TemporaryDirectory(prefix='mantech-native-solarian-') as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
    # Replay pre-fix callbacks with bounds-checking storage to establish the old failure.
    old = subprocess.check_output(['git','-c',f'safe.directory={root.as_posix()}',
        '-C',str(root),'show',f'HEAD:{relative}'],text=True)
    if 'bool ValidateSplitSpotlights()' not in old:
        old_methods = '\n'.join(block(old, marker) for marker in (
            'void Reset() override','void HandleSplitAgents()','void HandleSplitPriests()'))
        old_code = code[:code.index('int main()')].replace(methods,old_methods)
        old_code += '''int main(){Map map;Creature boss;boss.map=&map;AI ai(&boss);
        bool trapped=false;try{ai.HandleSplitAgents();}catch(const std::out_of_range&){trapped=true;}
        assert(trapped);std::cout<<"PASS: reproduced pre-fix unchecked empty spotlight indexing\\n";}'''
        (tmp/'old.cpp').write_text(old_code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','old.cpp','/Fe:old.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'old.exe')],cwd=tmp,check=True)
for action in ('SOLARIAN_PHASE_2_DELAY','SOLARIAN_SPLIT_PHASE_DELAY','SOLARIAN_SPLIT_AGENTS','SOLARIAN_SPLIT_PRIESTS'):
    line = next(line for line in source.splitlines() if f'AddCustomAction({action},' in line)
    assert 'TIMER_COMBAT_COMBAT' in line, action
timer = (root/'src/game/AI/ScriptDevAI/base/TimerAI.cpp').read_text()
assert 'data.second.combatSetting != TIMER_ALWAYS' in block(timer,'void TimerManager::ResetTimersOnEvade()')
assert 'data.second.ResetTimer()' in block(timer,'void TimerManager::ResetTimersOnEvade()')
print('PASS: all four delayed phase callbacks use native reset-on-evade combat timers')
