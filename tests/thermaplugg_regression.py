"""Exercise the actual Thermaplugg spell handler; run in a VS developer shell."""
from pathlib import Path
import sys,subprocess,tempfile
repo=Path(sys.argv[1])
f=repo/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/gnomeregan/boss_thermaplugg.cpp'
s=f.read_text();a=s.index('struct ActivateBombThermaplugg');b=s.index('\n};',a)+3
handler=s[a:b]
fixture=r'''
#include <cassert>
#include <iostream>
constexpr unsigned MAX_GNOME_FACES=6;
unsigned rolls=0;
unsigned urand(unsigned lo,unsigned hi){assert(lo==0&&hi==5);++rolls;return 3;}
struct InstanceData{virtual ~InstanceData()=default;};
struct instance_gnomeregan:InstanceData{unsigned activations=0,index=0;void DoActivateBombFace(unsigned i){++activations;index=i;}};
struct Unit{InstanceData* instance;InstanceData* GetInstanceData(){return instance;}};
using SpellEffectIndex=int;
struct Spell{Unit* caster;Unit* target;Unit* GetCaster(){return caster;}Unit* GetUnitTarget(){return target;}};
struct SpellScript{virtual void OnEffectExecute(Spell*,SpellEffectIndex)const{}};
'''
tests=r'''
int main(){
 ActivateBombThermaplugg script;instance_gnomeregan own,other;Unit caster{&own},target{&other};
 Spell destination{&caster,nullptr};script.OnEffectExecute(&destination,0);
 assert(own.activations==1&&own.index==3&&rolls==1);
 Spell withTarget{&caster,&target};script.OnEffectExecute(&withTarget,0);
 assert(own.activations==2&&other.activations==0&&rolls==2);
 Unit outside{nullptr};Spell noInstance{&outside,nullptr};script.OnEffectExecute(&noInstance,0);
 InstanceData wrong;Unit elsewhere{&wrong};Spell wrongInstance{&elsewhere,nullptr};script.OnEffectExecute(&wrongInstance,0);
 Spell noCaster{nullptr,&target};script.OnEffectExecute(&noCaster,0);
 assert(own.activations==2&&other.activations==0&&rolls==2);
 std::cout<<"PASS: targetless bomb activation, caster instance, one selection, absent/wrong instance and absent caster\n";
}
'''
with tempfile.TemporaryDirectory(prefix='thermaplugg-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(fixture+handler+tests)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],check=True)
