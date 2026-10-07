"""Exercise native spell startup/event ownership with reentrant caster cleanup.

Uses production SpellStart, cast admission, SpellEvent ownership/destruction,
EventProcessor, and UniqueTrackablePtr. Cast effects/caster callbacks are test
doubles. This is not an in-game replay of the production crash.
"""
from pathlib import Path
import subprocess,sys,tempfile

def block(s,marker):
    a=s.index(marker);start=s.index('{',a);depth=0
    for i in range(start,len(s)):
        depth+=(s[i]=='{')-(s[i]=='}')
        if not depth:return s[a:i+1]
    raise ValueError(marker)

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
source=(root/'src/game/Spells/Spell.cpp').read_text()
if '--before' in sys.argv:
    source=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),
        'show','HEAD:src/game/Spells/Spell.cpp'],text=True)
start=block(source,'SpellCastResult Spell::SpellStart(')
cast=block(source,'SpellCastResult Spell::cast(')
cast=cast[:cast.index('    SetExecutedCurrently(true);')] + '''
    SetExecutedCurrently(true);
    ++castCalls;
    if (scenario == 4) m_trueCaster->m_events.KillAllEvents(false);
    finish(true);
    SetExecutedCurrently(false);
    return SPELL_CAST_OK;
}'''
eventctor=block(source,'SpellEvent::SpellEvent(')
eventdtor=block(source,'SpellEvent::~SpellEvent(')

code=r'''
#include <cassert>
#include <stdexcept>
#include <string>
#include <iostream>
#include "EventProcessor.h"
#include "UniqueTrackablePtr.h"
enum {SPELL_STATE_CREATED,SPELL_STATE_TARGETING,SPELL_STATE_CASTING,SPELL_STATE_FINISHED};
enum SpellCastResult {SPELL_CAST_OK,SPELL_FAILED_ERROR,SPELL_FAILED_NO_POWER,SPELL_FAILED_SPELL_IN_PROGRESS};
enum {TYPEID_PLAYER};
int scenario=0,destroyed=0,prepared=0,castCalls=0,leaks=0;
bool inStart=false,earlyDestroyed=false;
struct Log {template<class... T>void outError(const char*,T...){++leaks;}} sLog;
struct World {static bool IsStopped(){return false;}};
struct SpellEntry {unsigned Id=19438;};
struct Aura {SpellEntry* GetSpellProto(){return nullptr;}};
struct Item {unsigned GetEntry(){return 0;}};
struct SpellCastTargets {};
struct Unit {void SetNextUpdateTime(unsigned){} bool IsUnit(){return true;} bool IsNonMeleeSpellCasted(bool,bool,bool){return false;} EventProcessor m_events;unsigned GetTypeId(){return TYPEID_PLAYER;}unsigned GetGUIDLow(){return 1;}};
struct SpellEvent;
struct Spell {
 Unit* m_trueCaster;Unit* m_caster;SpellEvent* m_spellEvent=nullptr;
 SpellEntry entry;SpellEntry const* m_spellInfo=&entry;SpellEntry const* m_triggeredByAuraSpell=nullptr;
 SpellCastTargets m_targets;Item* m_CastItem=nullptr;int m_spellState=SPELL_STATE_CREATED;
 unsigned m_cast_count=0;bool m_ignoreConcurrentCasts=false;bool m_executedCurrently=false,m_referencedFromCurrentSpell=false;
 explicit Spell(Unit* u):m_trueCaster(u),m_caster(u){}
 ~Spell(){++destroyed;if(inStart)earlyDestroyed=true;}
 bool IsDeletable()const{return !m_executedCurrently&&!m_referencedFromCurrentSpell;}
 void SetExecutedCurrently(bool v){m_executedCurrently=v;}
 Unit* GetCaster(){return m_caster;}int getState(){return m_spellState;}
 void cancel(){finish(false);}void finish(bool){m_spellState=SPELL_STATE_FINISHED;}
 void SendCastResult(SpellCastResult){}void SendInterrupted(SpellCastResult){}
 SpellCastResult SpellStart(SpellCastTargets const*,Aura* =nullptr);
 SpellCastResult cast(bool=false);
 SpellCastResult PreCastCheck(){
  if(scenario==1)return SPELL_FAILED_NO_POWER;
  if(scenario==2){m_trueCaster->m_events.KillAllEvents(false);if(earlyDestroyed)throw std::runtime_error("spell deleted inside PreCastCheck");}
  return SPELL_CAST_OK;
 }
 void Prepare(){
  ++prepared;m_spellState=SPELL_STATE_CASTING;
  if(scenario==3){m_trueCaster->m_events.KillAllEvents(false);if(earlyDestroyed)throw std::runtime_error("spell deleted inside Prepare");}
  cast();
 }
};
struct SpellEvent:BasicEvent {
 MaNGOS::unique_trackable_ptr<Spell> m_Spell;
 explicit SpellEvent(Spell*);~SpellEvent();
 MaNGOS::unique_weak_ptr<Spell> GetSpellWeakPtr()const{return m_Spell;}
 bool IsDeletable()const override{return m_Spell->IsDeletable();}
 void Abort(uint64)override{m_Spell->cancel();}
};
''' + '\n'.join((eventctor,eventdtor,start,cast)) + r'''
int main(){
 try {
  for(scenario=0;scenario<=4;++scenario){
   destroyed=prepared=castCalls=leaks=0;earlyDestroyed=false;
   Unit caster;SpellCastTargets target;Spell* spell=new Spell(&caster);
   inStart=true;auto result=spell->SpellStart(&target);inStart=false;
   if(earlyDestroyed)throw std::runtime_error("spell destroyed before SpellStart returned");
   if(scenario==1)assert(result==SPELL_FAILED_NO_POWER&&prepared==0&&castCalls==0);
   else if(scenario==2)assert(result==SPELL_FAILED_ERROR&&prepared==0&&castCalls==0&&destroyed==1);
   else if(scenario==3)assert(prepared==1&&castCalls==0&&destroyed==1);
   else assert(result==SPELL_CAST_OK&&prepared==1&&castCalls==1);
   caster.m_events.KillAllEvents(false);
   assert(destroyed==1&&leaks==0);
  }
 }catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}
 std::cout<<"spell startup: normal, rejection, cleanup during check/preparation/effect passed\n";
}
'''
# Destruction when the function's final local guard leaves scope is correct.
# Observe only callback-time destruction (before the guard is unwound).
code=code.replace('if(earlyDestroyed)throw std::runtime_error("spell destroyed before SpellStart returned");','')
with tempfile.TemporaryDirectory(prefix='spell-start-regression-') as td:
    temp=Path(td);(temp/'Platform').mkdir()
    (temp/'Platform/Define.h').write_text('#pragma once\n#include <cstdint>\nusing uint64=uint64_t;using uint32=uint32_t;\n')
    cpp=temp/'test.cpp';cpp.write_text(code);exe=temp/'test.exe'
    args=['cl','/nologo','/std:c++17','/EHsc','/W3','/I'+str(temp),
        '/I'+str(root/'src/framework/Utilities'),'/I'+str(root/'src/shared/Util'),str(cpp),
        str(root/'src/framework/Utilities/EventProcessor.cpp'),'/Fe:'+str(exe)]
    compile_result=subprocess.run(args,cwd=temp,capture_output=True,text=True)
    if compile_result.returncode:print(compile_result.stdout+compile_result.stderr);sys.exit(compile_result.returncode)
    run=subprocess.run([str(exe)],capture_output=True,text=True)
    print(root.name,run.stdout+run.stderr,end='');sys.exit(run.returncode)
