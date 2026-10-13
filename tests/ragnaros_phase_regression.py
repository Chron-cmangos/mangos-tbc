"""Exercise the native phase and actual summon/death callbacks, including late Sons."""
from pathlib import Path
import subprocess,sys,tempfile,shutil,os
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
s=(root/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/molten_core/boss_ragnaros.cpp').read_text()
if '--before' in sys.argv:
 s=subprocess.check_output(['git','-c','safe.directory=*','-C',str(root),'show','HEAD:src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/molten_core/boss_ragnaros.cpp'],text=True)
def block(marker):
 start=s.index(marker);begin=s.index('{',start);depth=0
 for end in range(begin,len(s)):
  depth+=(s[end]=='{')-(s[end]=='}')
  if not depth:return s[start:end+1].replace(' override','')
methods='\n'.join(block(x) for x in ('void SummonedCreatureJustDied(', 'void JustSummoned(', 'void HandlePhaseTransition('))
code=r'''
#include <cassert>
#include <algorithm>
#include <vector>
#include <map>
#include <set>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;using GuidVector=std::vector<unsigned>;
enum {SAY_REINFORCEMENTS_1,SAY_REINFORCEMENTS_2,UNIT_FIELD_FLAGS,UNIT_FLAG_UNINTERACTIBLE,
UNIT_STAND_STATE_CUSTOM,UNIT_STAND_STATE_STAND,CAST_TRIGGERED,CAST_AURA_NOT_PRESENT,TRIGGERED_OLD_TRIGGERED,CAST_OK};
enum {SPELL_RAGNA_SUBMERGE=21107,SPELL_RAGNA_SUBMERGE_VISUAL=20567,SPELL_SUBMERGE_EFFECT=21859,SPELL_RAGNA_EMERGE=20568,
 SPELL_SUMMON_SONS_FLAME=21108,SPELL_DOUBLE_ATTACK=19818,SPELL_LAVA_SHIELD=21857,SPELL_INTENSE_HEAT=21155,
 NPC_SON_OF_FLAME=12143,NPC_FLAME_OF_RAGNAROS=13148,PHASE_EMERGING=0,PHASE_EMERGED=1,PHASE_SUBMERGING=2,PHASE_SUBMERGED=3,
 RAGNAROS_PHASE_TRANSITION=0,RAGNAROS_WRATH_OF_RAGNAROS,RAGNAROS_MIGHT_OF_RAGNAROS,RAGNAROS_MAGMA_BLAST,RAGNAROS_LAVA_BURST};
constexpr unsigned IN_MILLISECONDS=1000,MINUTE=60,NB_ADDS_IN_SUBMERGE=8;
unsigned urand(unsigned a,unsigned){return a;}
struct SonAI{void DoCastSpellIfCan(void*,unsigned,unsigned){}void AttackClosestEnemy(){}};
struct Creature {unsigned entry=NPC_SON_OF_FLAME,guid=1,stand=0;bool flag=false;std::set<unsigned>auras;SonAI ai;
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}SonAI*AI(){return &ai;}
 void SetInCombatWithZone(){}void CastSpell(void*,unsigned,unsigned,void*,void*,unsigned){}
 void SetStandState(unsigned n){stand=n;}void SetFlag(unsigned,unsigned){flag=true;}void RemoveFlag(unsigned,unsigned){flag=false;}
 void RemoveAurasDueToSpell(unsigned n){auras.erase(n);}};
void DoScriptText(unsigned,Creature*){}
struct Rag {Creature*m_creature;uint32 m_uiAddCount=0,m_phase=PHASE_EMERGED;bool m_bHasSubmergedOnce=false,m_sonsSummoned=false,melee=true;
 GuidVector m_spawns,m_sons;std::map<unsigned,unsigned>timers;std::set<unsigned>disabled;unsigned nextGuid=1,summons=8;
 void ResetCombatAction(unsigned a,unsigned t){timers[a]=t;disabled.erase(a);}void ReduceTimer(unsigned a,unsigned t){timers[a]=std::min(timers[a],t);}
 void DisableCombatAction(unsigned a){disabled.insert(a);}void SetMeleeEnabled(bool v){melee=v;}
 unsigned DoCastSpellIfCan(Creature*,unsigned spell,unsigned flags=0){
  if(spell==SPELL_SUMMON_SONS_FLAME){for(unsigned i=0;i<summons;++i){Creature son;son.guid=nextGuid++;JustSummoned(&son);}return CAST_OK;}
  m_creature->auras.insert(spell);return CAST_OK;}
 __METHODS__
};
int main(){
 Creature boss;Rag ai{&boss};
 ai.HandlePhaseTransition();assert(ai.m_phase==PHASE_SUBMERGING&&ai.m_uiAddCount==8&&!ai.melee&&boss.flag&&ai.timers[0]==3000);
 ai.HandlePhaseTransition();assert(ai.m_phase==PHASE_SUBMERGED&&ai.timers[0]==90000);
 // The timer may expire with Sons still alive. Last old Son death after emerge
 // must not shorten the new 180-second surface phase to one second.
 ai.HandlePhaseTransition();assert(ai.m_phase==PHASE_EMERGING&&ai.timers[0]==500);
 ai.HandlePhaseTransition();assert(ai.m_phase==PHASE_EMERGED&&ai.timers[0]==180000&&ai.melee&&!boss.flag);
 for(unsigned guid=1;guid<=8;++guid){Creature son;son.guid=guid;ai.SummonedCreatureJustDied(&son);}assert(ai.timers[0]==180000);
 ai.HandlePhaseTransition();assert(ai.m_uiAddCount==8&&ai.m_sons.front()==9);
 Creature old;old.guid=8;ai.SummonedCreatureJustDied(&old);assert(ai.m_uiAddCount==8);
 ai.HandlePhaseTransition();
 for(unsigned guid=9;guid<=16;++guid){Creature son;son.guid=guid;ai.SummonedCreatureJustDied(&son);ai.SummonedCreatureJustDied(&son);}
 assert(ai.m_uiAddCount==0&&ai.timers[0]==1000); // duplicate callbacks cannot underflow
 ai.HandlePhaseTransition();ai.HandlePhaseTransition();assert(ai.timers[0]==180000);
 ai.HandlePhaseTransition();for(unsigned guid=17;guid<=24;++guid){Creature son;son.guid=guid;ai.SummonedCreatureJustDied(&son);}
 ai.HandlePhaseTransition();assert(ai.m_phase==PHASE_SUBMERGED&&ai.timers[0]==1000); // fast clear during 3s animation
 std::cout<<"PASS: native phase timing, late-wave deaths, duplicate/stale callbacks, eight actual summons, rapid Sons clear\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='native-ragnaros-') as folder:
 d=Path(folder);(d/'test.cpp').write_text(code)
 compiler=os.environ.get('CXX') or ('cl' if shutil.which('cl') else 'c++')
 if Path(compiler).stem.lower()=='cl':cmd=[compiler,'/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'];exe=d/'test.exe'
 else:cmd=[compiler,'-std=c++17','test.cpp','-o','test'];exe=d/'test'
 subprocess.run(cmd,cwd=d,check=True);subprocess.run([str(exe)],cwd=d,check=True)
