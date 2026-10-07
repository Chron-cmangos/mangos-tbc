"""Compile actual dummy initialization/update code against controlled core objects."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
def block(text,marker):
    start=text.index(marker); opening=text.index('{',start); depth=1; end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
source=(root/'src/modules/trainingdummies/src/TrainingdummiesModule.cpp').read_text()
methods='\n'.join(block(source,marker) for marker in (
    'void TrainingdummiesModule::Initialize(',
    'void TrainingdummiesModule::OnUpdate('))
code=r'''
#include <cassert>
#include <map>
#include <iostream>
using uint32=unsigned;using int32=int;
enum {UNIT_STAT_NO_COMBAT_MOVEMENT=4,REACT_PASSIVE=0};
struct CreatureAI {int react=2;void SetReactState(int state){react=state;}};
struct Creature {CreatureAI ai;unsigned states=0,stops=0;CreatureAI* AI(){return &ai;}
 void addUnitState(unsigned state){states|=state;}void CombatStop(){++stops;}};
struct TrainingDummyStatus {bool initialized=false;int32 combatTimer=0;};
struct Config {bool enabled=true;};
struct TrainingdummiesModule {Config config;Creature* dummy=nullptr;
 std::map<unsigned,TrainingDummyStatus> trainingDummyStatus;
 Config* GetConfig(){return &config;}Creature* GetDummyCreature(const TrainingDummyStatus&){return dummy;}
 void Initialize(TrainingDummyStatus&);void OnUpdate(uint32);
};
__METHODS__
int main(){
 TrainingdummiesModule module;Creature dummy;auto& status=module.trainingDummyStatus[1];
 module.OnUpdate(1);assert(!status.initialized);
 module.dummy=&dummy;module.OnUpdate(1);
 assert(status.initialized && dummy.ai.react==REACT_PASSIVE && (dummy.states&UNIT_STAT_NO_COMBAT_MOVEMENT));
 status.combatTimer=10000;module.OnUpdate(9000);assert(status.combatTimer==1000 && dummy.stops==0);
 module.OnUpdate(999);assert(status.combatTimer==1 && dummy.stops==0);
 module.OnUpdate(1);assert(status.combatTimer==0 && dummy.stops==1);
 module.OnUpdate(1000);assert(dummy.stops==1);
 status.combatTimer=10000;module.OnUpdate(15000);assert(status.combatTimer==0 && dummy.stops==2);
 status.combatTimer=10000;module.config.enabled=false;module.OnUpdate(15000);
 assert(status.combatTimer==10000 && dummy.stops==2);
 std::cout<<"PASS: native dummy module sets passive/no-combat-movement and resets combat after inactivity, not on every tick\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-dummy-test-') as tmp:
    tmp=Path(tmp);(tmp/'probe.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','probe.cpp','/Fe:probe.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'probe.exe')],check=True)
# The native core itself enforces the passive state before starting an attack.
native=(root/'src/game/AI/BaseAI/CreatureAI.cpp').read_text()
attack=block(native,'void CreatureAI::AttackStart(')
assert 'HasReactState(REACT_PASSIVE)' in attack
damage=block(source,'void TrainingdummiesModule::OnDealDamage(')
assert 'IsTrainingDummy(victim)' in damage and 'status.combatTimer = 10000' in damage
print('PASS: native attack-start passive guard and damage-reset hook are present')
