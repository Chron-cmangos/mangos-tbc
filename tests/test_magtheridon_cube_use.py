"""Compile the actual native cube-use script; no running world is required."""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
source=(root/'src/game/AI/ScriptDevAI/scripts/outland/hellfire_citadel/magtheridons_lair/boss_magtheridon.cpp').read_text()
def block(text, marker):
    start=text.index(marker); opening=text.index('{',start); depth=0
    for i in range(opening,len(text)):
        if text[i]=='{': depth+=1
        elif text[i]=='}':
            depth-=1
            if not depth: return text[start:i+1]
    raise AssertionError(marker)
methods=block(source,'struct go_manticron_cubeAI')+';\n'+block(source,'bool GOUse_go_manticron_cube(')
code=r'''
#include <cassert>
#include <map>
#include <set>
#include <iostream>
using ObjectGuid=unsigned;
constexpr unsigned SPELL_MIND_EXHAUSTION=44032,SPELL_SHADOW_GRASP=30410,TRIGGERED_NONE=0,
 SPELL_CAST_OK=0,TYPE_MAGTHERIDON_EVENT=0,IN_PROGRESS=1,NPC_MAGTHERIDON=17257;
struct Player{unsigned guid;std::set<unsigned> auras;unsigned attempts=0,result=0;
 bool HasAura(unsigned spell){return auras.count(spell);}ObjectGuid GetObjectGuid(){return guid;}
 unsigned CastSpell(void* target,unsigned spell,unsigned flags){
 assert(!target&&spell==SPELL_SHADOW_GRASP&&flags==TRIGGERED_NONE);++attempts;
 if(result==SPELL_CAST_OK)auras.insert(spell);return result;}};
struct Creature{bool alive=true;bool IsAlive(){return alive;}};
struct ScriptedInstance{unsigned state=IN_PROGRESS;Creature* boss=nullptr;
 unsigned GetData(unsigned type){assert(type==TYPE_MAGTHERIDON_EVENT);return state;}
 Creature* GetSingleCreatureFromStorage(unsigned entry){assert(entry==NPC_MAGTHERIDON);return boss;}};
struct Map{std::map<unsigned,Player*> players;Player* GetPlayer(ObjectGuid guid){
 auto i=players.find(guid);return i==players.end()?nullptr:i->second;}};
struct GameObjectAI;
struct GameObject{Map* map;GameObjectAI* ai=nullptr;ScriptedInstance* instance=nullptr;
 Map* GetMap(){return map;}GameObjectAI* AI(){return ai;}ScriptedInstance* GetInstanceData(){return instance;}};
struct GameObjectAI{GameObject* m_go;GameObjectAI(GameObject* go):m_go(go){}virtual ~GameObjectAI()=default;};
__METHODS__
int main(){
 Map map;Player first{1},second{2};map.players={{1,&first},{2,&second}};
 Creature boss;ScriptedInstance instance{IN_PROGRESS,&boss};
 GameObject cube{&map,nullptr,&instance},otherCube{&map,nullptr,&instance};
 go_manticron_cubeAI ai(&cube),otherAI(&otherCube);cube.ai=&ai;otherCube.ai=&otherAI;
 assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==1&&ai.GetManticronCubeLastUser()==&first);
 assert(GOUse_go_manticron_cube(&second,&cube)&&second.attempts==0); // GO auto-close must not release an active channel.
 assert(GOUse_go_manticron_cube(&first,&otherCube)&&first.attempts==1); // One user cannot start another cube while channeling.
 assert(GOUse_go_manticron_cube(&second,&otherCube)&&second.attempts==1&&otherAI.GetManticronCubeLastUser()==&second);
 first.auras.clear();first.auras.insert(SPELL_MIND_EXHAUSTION);
 assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==1);
 first.auras.clear();second.auras.clear();second.result=7;
 assert(GOUse_go_manticron_cube(&second,&cube)&&second.attempts==2&&ai.GetManticronCubeLastUser()==&first);
 second.result=SPELL_CAST_OK;assert(GOUse_go_manticron_cube(&second,&cube)&&ai.GetManticronCubeLastUser()==&second);
 map.players.erase(2);assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==2&&ai.GetManticronCubeLastUser()==&first);
 first.auras.clear();unsigned attempts=first.attempts;
 instance.state=0;assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==attempts);instance.state=IN_PROGRESS;
 boss.alive=false;assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==attempts);boss.alive=true;
 instance.boss=nullptr;assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==attempts);instance.boss=&boss;
 cube.instance=nullptr;assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==attempts);cube.instance=&instance;
 cube.ai=nullptr;assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==attempts);
 GameObjectAI wrong(&cube);cube.ai=&wrong;assert(GOUse_go_manticron_cube(&first,&cube)&&first.attempts==attempts);
 std::cout<<"PASS: actual native cube ownership, one-channel rule, exhaustion, cast failure, release and wrong-AI safety\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-native-cube-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
assert 'target->GetAuraCount(30166) == 5' in source
assert 'InterruptSpell(CURRENT_CHANNELED_SPELL)' in block(source,'struct ShadowGraspMagth')
assert 'SPELL_MIND_EXHAUSTION, TRIGGERED_OLD_TRIGGERED' in block(source,'struct ShadowGraspCube')
print('PASS: native five-beam interruption and exhaustion code retained; real channel playback remains a dev test')
