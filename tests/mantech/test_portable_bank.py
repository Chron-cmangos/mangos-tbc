"""Exercise the production personal-bank summon and real backfill predicate.
Run with Python from an x64 Visual Studio developer shell. No server binary is built.
"""
from pathlib import Path
import re, sqlite3, subprocess, tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/game/AI/ScriptDevAI/scripts/world/item_scripts.cpp').read_text()
start=source.index('    struct ManTechPortableBankSpell : public SpellScript')
brace=source.index('{',start);depth=0
for end in range(brace,len(source)):
    depth+=(source[end]=='{')-(source[end]=='}')
    if not depth:break
method=source[start:end+1]+';'
code=r"""
#include <cassert>
#include <iostream>
using uint32=unsigned;
enum{SPELL_CAST_OK,SPELL_FAILED_NOT_HERE,TYPEID_PLAYER=4,TEMPSPAWN_TIMED_DESPAWN=1};
using SpellCastResult=int;constexpr uint32 UNIT_NPC_FLAG_BANKER=__FLAG__;
constexpr float DEFAULT_WORLD_OBJECT_SIZE=0.5f;
struct CreatureInfo{uint32 NpcFlags=UNIT_NPC_FLAG_BANKER;};
CreatureInfo info;bool templateExists=true;
struct ObjectMgr{static CreatureInfo const*GetCreatureTemplate(uint32 id){assert(id==65004);return templateExists?&info:nullptr;}};
struct Session{unsigned notices=0;void SendNotification(char const*){++notices;}};
struct SpellEntry{uint32 Id=7977;};
struct WorldObject{bool world=true;unsigned type=TYPEID_PLAYER;virtual ~WorldObject()=default;
 bool IsInWorld(){return world;}unsigned GetTypeId(){return type;}};
struct Player:WorldObject{Session session;unsigned summons=0,cleared=0;bool spawnOK=true;
 void GetClosePoint(float&x,float&y,float&z,float size,float range){assert(size==0.5f&&range==1);x=10;y=20;z=30;}
 float GetOrientation(){return 1.5f;}
 bool SummonCreature(unsigned entry,float x,float y,float z,float orientation,int type,unsigned duration,bool active,bool run,unsigned path,unsigned faction){
  assert(entry==65004&&x==10&&y==20&&z==30&&orientation==1.5f);
  assert(type==TEMPSPAWN_TIMED_DESPAWN&&duration==600000&&!active&&!run&&!path&&faction==35);++summons;return spawnOK;
 }
 Session*GetSession(){return &session;}void RemoveSpellCooldown(SpellEntry const&s){cleared=s.Id;}
};
struct Item{unsigned id=65004;unsigned GetEntry(){return id;}};
struct Spell{Item*item;WorldObject*caster;SpellEntry entry;SpellEntry*m_spellInfo=&entry;
 Item*GetCastItem(){return item;}WorldObject*GetTrueCaster(){return caster;}};
struct SpellScript{virtual SpellCastResult OnCheckCast(Spell*,bool)const{return SPELL_CAST_OK;}virtual void OnCast(Spell*)const{}};
__METHOD__
int main(){
 Player p;Item item;Spell spell{&item,&p};ManTechPortableBankSpell bank;
 assert(bank.OnCheckCast(&spell,true)==SPELL_CAST_OK);bank.OnCast(&spell);assert(p.summons==1&&!p.cleared&&!p.session.notices);
 for(unsigned id:{65000u,65001u,65002u,65003u,6948u}){item.id=id;assert(bank.OnCheckCast(&spell,true)==SPELL_CAST_OK);bank.OnCast(&spell);assert(p.summons==1);}
 item.id=65004;spell.item=nullptr;assert(bank.OnCheckCast(&spell,true)==SPELL_CAST_OK);bank.OnCast(&spell);assert(p.summons==1);spell.item=&item;
 spell.caster=nullptr;assert(bank.OnCheckCast(&spell,true)==SPELL_FAILED_NOT_HERE);bank.OnCast(&spell);spell.caster=&p;
 p.world=false;assert(bank.OnCheckCast(&spell,true)==SPELL_FAILED_NOT_HERE);bank.OnCast(&spell);p.world=true;
 p.type=3;assert(bank.OnCheckCast(&spell,true)==SPELL_FAILED_NOT_HERE);bank.OnCast(&spell);p.type=TYPEID_PLAYER;assert(p.summons==1);
 templateExists=false;assert(bank.OnCheckCast(&spell,true)==SPELL_FAILED_NOT_HERE);bank.OnCast(&spell);assert(p.summons==1&&p.cleared==7977);templateExists=true;
 p.cleared=0;info.NpcFlags=0;assert(bank.OnCheckCast(&spell,true)==SPELL_FAILED_NOT_HERE);bank.OnCast(&spell);assert(p.summons==1&&p.cleared==7977);info.NpcFlags=UNIT_NPC_FLAG_BANKER;
 p.cleared=0;p.spawnOK=false;bank.OnCast(&spell);assert(p.summons==2&&p.cleared==7977);
 p.spawnOK=true;p.cleared=0;bank.OnCast(&spell);assert(p.summons==3&&!p.cleared);
 std::cout<<"PASS personal bank: real script, independent carrier, ten-minute banker, lifecycle, wrong item and failed-summon refund\n";
}
""".replace('__METHOD__',method)
native=(root/'src/game/Entities/Unit.h').read_text()
flag=int(re.search(r'UNIT_NPC_FLAG_BANKER\s*=\s*(0x[0-9A-Fa-f]+)',native)[1],16)
code=code.replace('__FLAG__',str(flag))
with tempfile.TemporaryDirectory(prefix='mantech-personal-bank-') as tmp:
    tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl.exe','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],check=True)

# Run the exact startup-selection SQL against eligible/deleted/unowned/legacy rows.
grant=(root/'src/game/Mails/ManTechPortableUtilityGrant.cpp').read_text()
selection=grant.split('void ManTechPortableUtilityGrant::BackfillExistingCharacters()',1)[1].split('CharacterDatabase.Query(',1)[1].split(');',1)[0]
query=''.join(re.findall(r'"([^"\n]*)"',selection))
db=sqlite3.connect(':memory:')
db.executescript('CREATE TABLE characters(guid INTEGER,account INTEGER,deleteDate INTEGER,level INTEGER); CREATE TABLE mantech_character_grants(guid INTEGER,grant_key TEXT);')
old=['portable_mailbox_v1','portable_repair_v1','portable_auctioneer_v1']
for guid in range(1,7):
    db.execute('INSERT INTO characters VALUES(?,?,?,?)',(guid,0 if guid==4 else 1,123 if guid==5 else None,1))
    for key in old:db.execute('INSERT INTO mantech_character_grants VALUES(?,?)',(guid,key))
db.execute("INSERT INTO mantech_character_grants VALUES(2,'portable_bank_v1')")
db.execute("DELETE FROM mantech_character_grants WHERE guid=3")
db.execute("INSERT INTO mantech_character_grants VALUES(3,'portable_utilities_v1')")
assert [row[0] for row in db.execute(query)]==[1,3,6]
db.execute("INSERT INTO mantech_character_grants VALUES(1,'portable_bank_v1')")
assert [row[0] for row in db.execute(query)]==[3,6]
print('PASS actual startup predicate: existing players get missing bank; complete/deleted/unowned characters excluded')
