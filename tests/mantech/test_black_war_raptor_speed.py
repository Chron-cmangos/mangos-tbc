"""Compile the actual mounted-speed aura handler with mocked native boundaries."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/game/Spells/SpellAuras.cpp').read_text()
start=source.index('void Aura::HandleAuraModIncreaseMountedSpeed(')
opening=source.index('{',start);depth=0
for end in range(opening,len(source)):
    depth+=(source[end]=='{')-(source[end]=='}')
    if depth==0:break
method=source[start:end+1]
castsource=(root/'src/game/Spells/Spell.cpp').read_text()
checkstart=castsource.index('    if (m_CastItem && m_CastItem->GetEntry() == 65003 && m_spellInfo->Id == 22721 &&',castsource.index('SpellCastResult Spell::CheckCast('))
opening=castsource.index('{',checkstart);depth=0
for end in range(opening,len(castsource)):
    depth+=(castsource[end]=='{')-(castsource[end]=='}')
    if depth==0:break
check=castsource[checkstart:end+1]
method+='\nint CheckRewardMount(Player* m_trueCaster, int id, int itemId=65003) { Item item{itemId}; Item* m_CastItem=itemId<0?nullptr:&item; struct {int Id;} info{id}; auto m_spellInfo=&info;'+check+' return 0; }'
sql=(root/'sql/custom/world/20260911_01_black_war_raptor_reward.sql').read_text()
assert 'WHERE entry=18246' in sql and 'SET entry=65003' in sql and 'UPDATE item_template' not in sql and 'Flags=32' in sql and 'SellPrice=0' in sql and 'maxcount=1' in sql and 'spellcharges_1=0' in sql and 'AllowableRace=-1' in sql and 'RequiredLevel=40' in sql and 'RequiredSkillRank=75' in sql and 'requiredhonorrank=0' in sql
player=(root/'src/game/Entities/Player.cpp').read_text()
assert 'if (IsInWorld() && level >= 40)' in player and 'SendItemQuerySingleResponse(65003)' in player

prefix=r'''
#include <cassert>
#include <iostream>
enum {TYPEID_PLAYER=4, MOVE_RUN=1, SKILL_RIDING=762, SPELL_AURA_MOD_INCREASE_MOUNTED_SPEED=32, TRIGGERED_OLD_TRIGGERED=1, SPELL_FAILED_LOW_CASTLEVEL=10, SPELL_FAILED_MIN_SKILL=11};
struct Unit {
 int type=TYPEID_PLAYER,updates=0,casts=0;bool festive=false;
 int GetTypeId(){return type;}
 void UpdateSpeed(int movement,bool forced){assert(movement==MOVE_RUN && forced);++updates;}
 bool HasAura(int id){return festive && id==62061;}
 template<class T>void CastSpell(Unit*,int id,int,void*,T*){assert(id==25860);++casts;}
};
struct Item {int entry=65003;int GetEntry(){return entry;}};
struct Player:Unit {Item item;bool hasItem=true;Item* GetItemByGuid(int guid){return hasItem && guid==1?&item:nullptr;}int level=40,skill=75;int GetLevel(){return level;}int GetSkillValuePure(int id){assert(id==SKILL_RIDING);return skill;}};
struct Aura {
 Player player;int id=22721;
 struct {int m_auraname=32,m_amount=100;}m_modifier;
 struct Proto {int SpellIconID=0;}proto;
 int GetCastItemGuid(){return 1;}Unit* GetTarget(){return &player;}int GetId(){return id;}Proto* GetSpellProto(){return &proto;}
 void HandleAuraModIncreaseMountedSpeed(bool,bool);
};
'''
suffix=r'''
int main(){
 for(auto level:{39,40,60})for(auto skill:{0,74,75,150}){
  Player p;p.level=level;p.skill=skill;
  assert(CheckRewardMount(&p,22721)==(level<40?SPELL_FAILED_LOW_CASTLEVEL:skill<75?SPELL_FAILED_MIN_SKILL:0));
  assert(CheckRewardMount(&p,23221)==0);
  assert(CheckRewardMount(&p,22721,18246)==0);assert(CheckRewardMount(&p,22721,-1)==0);
 }

 for(auto level:{39,40,59,60,80})for(auto skill:{0,74,75,149,150,225,300}){
  Aura a;a.player.level=level;a.player.skill=skill;a.HandleAuraModIncreaseMountedSpeed(true,true);
  assert(a.m_modifier.m_amount==((level>=60 && skill>=150)?100:60));assert(a.player.updates==1);
 }
 Aura native;native.player.item.entry=18246;native.HandleAuraModIncreaseMountedSpeed(true,true);assert(native.m_modifier.m_amount==100);
 native={};native.player.hasItem=false;native.HandleAuraModIncreaseMountedSpeed(true,true);assert(native.m_modifier.m_amount==100);
 Aura a;a.id=23221;a.HandleAuraModIncreaseMountedSpeed(true,true);assert(a.m_modifier.m_amount==100);
 a={};a.player.type=3;a.HandleAuraModIncreaseMountedSpeed(true,true);assert(a.m_modifier.m_amount==100);
 a={};a.HandleAuraModIncreaseMountedSpeed(false,true);assert(a.m_modifier.m_amount==100 && a.player.updates==1);
 a={};a.HandleAuraModIncreaseMountedSpeed(true,false);assert(a.m_modifier.m_amount==100 && a.player.updates==0);
 a={};a.m_modifier.m_auraname=130;a.m_modifier.m_amount=10;a.HandleAuraModIncreaseMountedSpeed(true,true);assert(a.m_modifier.m_amount==10);
 std::cout<<"PASS actual mount handler: level/skill matrix, other mounts, creatures, apply/remove, non-real updates and bonus aura isolation\n";
}
'''
with tempfile.TemporaryDirectory(prefix='mantech-mount-test-') as d:
    d=Path(d);(d/'test.cpp').write_text(prefix+method+suffix)
    subprocess.run(['cl.exe','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=d,check=True)
    subprocess.run([str(d/'test.exe')],check=True)
