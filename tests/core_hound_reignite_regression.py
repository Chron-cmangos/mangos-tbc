"""Run native Core Hound collapse/reignite code with controlled combat peers."""
from pathlib import Path
import subprocess,sys,tempfile,shutil,os
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
source=(root/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/molten_core/molten_coreScripts.cpp').read_text()
start=source.index('struct npc_core_hound :');opening=source.index('{',start);depth=0
for end in range(opening,len(source)):
 depth+=(source[end]=='{')-(source[end]=='}')
 if depth==0:break
body=source[start:end+1]+';'
assert '->Name = "npc_core_hound"' in source
code=r'''
#include <cassert>
#include <list>
#include <functional>
#include <set>
#include <iostream>
struct Unit{};
struct Creature{unsigned hp=1,stand=0;bool combat=true,despawn=false,suicide=false;std::set<unsigned>auras;
 bool IsInCombat(){return combat;}unsigned GetHealth(){return hp;}void SetStandState(unsigned s){stand=s;}
 void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}void SetTarget(void*){}
 void Suicide(){suicide=true;hp=0;}void ForcedDespawn(){despawn=true;}};
enum{UNIT_STAND_STATE_STAND,UNIT_STAND_STATE_DEAD,CAST_TRIGGERED};
std::list<Creature*>nearby;
void GetCreatureListWithEntryInGrid(std::list<Creature*>&out,Creature*,unsigned id,float range){assert(id==11671&&range==40);out=nearby;}
struct CreatureEventAI{Creature*m_creature;bool prevention=false,movement=true;unsigned timer=0,threatResets=0,emote=0,visuals=0;std::function<void()>callback;
 CreatureEventAI(Creature*c):m_creature(c){}virtual ~CreatureEventAI()=default;virtual void Reset(){timer=0;}virtual void JustPreventedDeath(Unit*){}
 void SetDeathPrevention(bool enabled){prevention=enabled;}
 void AddCustomAction(unsigned id,bool disabled,std::function<void()>fn){assert(id==0&&disabled);callback=fn;}
 void ResetTimer(unsigned id,unsigned delay){assert(id==0);timer=delay;}
 void DoCastSpellIfCan(void*,unsigned spell,unsigned flags){assert(flags==CAST_TRIGGERED);
  if(spell==17683)m_creature->hp=100;else if(spell==19951)m_creature->auras.insert(spell);else {assert(spell==19823);++visuals;}}
 void DoResetThreat(){++threatResets;}void SetCombatMovement(bool enabled){movement=enabled;}void DoBroadcastText(unsigned text,Creature*){emote=text;}};
__BODY__
int main(){
 Creature self,peer;nearby={&self,&peer};npc_core_hound ai(&self);assert(ai.prevention);ai.JustPreventedDeath(nullptr);
 assert(ai.timer==10000&&!ai.movement&&self.stand==UNIT_STAND_STATE_DEAD&&self.auras.count(19951));
 peer.hp=100;ai.callback();assert(self.hp==100&&self.stand==UNIT_STAND_STATE_STAND&&ai.movement&&ai.prevention);
 assert(!self.auras.count(19951)&&ai.threatResets==1&&ai.visuals==1&&ai.emote==7867&&!self.despawn);
 self=Creature{};peer.hp=1;ai.JustPreventedDeath(nullptr);ai.callback();assert(self.suicide&&self.despawn); // all collapsed
 self=Creature{};peer.hp=100;peer.combat=false;ai.Reset();ai.JustPreventedDeath(nullptr);ai.callback();
 assert(self.suicide&&self.despawn); // another unengaged pack cannot reignite this one
 self=Creature{};nearby={&self};ai.Reset();ai.JustPreventedDeath(nullptr);ai.callback();assert(self.suicide&&self.despawn);
 std::cout<<"PASS: native 10-second collapse, engaged peer reignite, all-collapsed completion, unrelated-pack exclusion\n";
}
'''.replace('__BODY__',body)
with tempfile.TemporaryDirectory(prefix='native-hound-') as folder:
 d=Path(folder);(d/'test.cpp').write_text(code)
 compiler=os.environ.get('CXX') or ('cl' if shutil.which('cl') else 'c++')
 if Path(compiler).stem.lower()=='cl':cmd=[compiler,'/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'];exe=d/'test.exe'
 else:cmd=[compiler,'-std=c++17','test.cpp','-o','test'];exe=d/'test'
 subprocess.run(cmd,cwd=d,check=True);subprocess.run([str(exe)],cwd=d,check=True)
