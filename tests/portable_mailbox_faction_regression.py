"""Execute production portable-mailbox faction assignment for both factions."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(sys.argv[1]);era=r.name
def block(source,needle):
 start=source.index(needle);brace=source.index('{',start);depth=0
 for end in range(brace,len(source)):
  depth+=(source[end]=='{')-(source[end]=='}')
  if not depth:return source[start:end+1]
if era=='wotlk':
 source=block((r/'src/game/Spells/SpellEffects.cpp').read_text(),'void Spell::EffectSummonObjectWild(')
 start=source.index('if (m_CastItem && m_CastItem->GetEntry() == 65000');body=source[start:source.index('\n\n',start)]
 main='''Item carrier;WorldObject caster;GameObject mailbox;auto*m_CastItem=&carrier;auto*m_trueCaster=&caster;auto*pGameObj=&mailbox;unsigned gameobject_id=142102;
 for(unsigned faction:{12u,29u,35u}){caster.faction=faction;mailbox.faction=55;__BODY__;assert(mailbox.faction==faction);}
 carrier.id=65001;mailbox.faction=55;__BODY__;assert(mailbox.faction==55);
 carrier.id=65000;gameobject_id=1;__BODY__;assert(mailbox.faction==55);
 gameobject_id=142102;caster.type=0;__BODY__;assert(mailbox.faction==55);
 m_CastItem=nullptr;__BODY__;assert(mailbox.faction==55);'''.replace('__BODY__',body)
else:
 body=block((r/'src/game/AI/ScriptDevAI/scripts/world/item_scripts.cpp').read_text(),'struct ManTechPortableMailboxSpell')+';'
 main='''Player caster;Item carrier;Spell spell{&carrier,&caster};ManTechPortableMailboxSpell script;
 for(unsigned faction:{12u,29u,35u}){caster.faction=faction;script.OnCast(&spell);assert(last.faction==faction&&last.spawner==9&&last.added);}
 carrier.id=65001;unsigned count=spawns;script.OnCast(&spell);assert(spawns==count);
 carrier.id=65000;createOK=false;script.OnCast(&spell);assert(spawns==count);'''
code=r'''
#include <cassert>
#include <initializer_list>
#include <iostream>
using uint32=unsigned;using SpellCastResult=int;
constexpr unsigned TYPEID_PLAYER=4,HIGHGUID_GAMEOBJECT=5,GAMEOBJECT_FACTION=7,GAMEOBJECT_TYPE_MAILBOX=19;
constexpr unsigned ITEM_MANTECH_PORTABLE_MAILBOX=65000,GO_PORTABLE_MAILBOX=142102,PORTABLE_MAILBOX_LIFETIME_SECONDS=600;
constexpr int SPELL_CAST_OK=0,SPELL_FAILED_NOT_HERE=1;constexpr float DEFAULT_WORLD_OBJECT_SIZE=0.5f;
struct GameObject;struct Map{unsigned GenerateLocalLowGuid(unsigned){return 1;}void Add(GameObject*);};Map map;
struct WorldObject{unsigned faction=29,type=TYPEID_PLAYER;unsigned GetFaction(){return faction;}unsigned GetTypeId(){return type;}bool IsInWorld(){return true;}
 Map*GetMap(){return &map;}void GetClosePoint(float&x,float&y,float&z,float,float){x=y=z=1;}float GetOrientation(){return 0;}unsigned GetObjectGuid(){return 9;}};
struct Session{void SendNotification(const char*){}};struct Player:WorldObject{Session session;Session*GetSession(){return &session;}template<class T>void RemoveSpellCooldown(T const&){} };
struct Item{unsigned id=65000;unsigned GetEntry(){return id;}};struct SpellInfo{unsigned Id=1206;};SpellInfo info;
struct Spell{Item*item;WorldObject*caster;SpellInfo*m_spellInfo=&info;Item*GetCastItem(){return item;}WorldObject*GetTrueCaster(){return caster;}};
struct SpellScript{virtual void OnCast(Spell*)const{}virtual SpellCastResult OnCheckCast(Spell*,bool)const{return SPELL_CAST_OK;}};
struct GameObjectInfo{unsigned type=GAMEOBJECT_TYPE_MAILBOX;};GameObjectInfo goinfo;
struct ObjectMgr{static GameObjectInfo const*GetGameObjectInfo(unsigned id){assert(id==142102);return &goinfo;}};
bool createOK=true;unsigned spawns=0;
struct GameObject{unsigned faction=55,spawner=0;bool added=false;
 static GameObject*CreateGameObject(unsigned id){assert(id==142102);return new GameObject;}
 bool Create(unsigned,unsigned,unsigned,Map*,float,float,float,float){if(createOK)++spawns;return createOK;}
 void SetRespawnTime(unsigned){}void SetSpellId(unsigned){}void SetSpawnerGuid(unsigned s){spawner=s;}
 void SetUInt32Value(unsigned field,unsigned v){assert(field==GAMEOBJECT_FACTION);faction=v;}void AIM_Initialize(){}};
GameObject last;void Map::Add(GameObject*g){g->added=true;last=*g;}
__METHOD__
int main(){__MAIN__ std::cout<<"PASS portable mailbox: Horde/Alliance faction and item scope; world template preserved\n";}
'''.replace('__METHOD__',body if era!='wotlk' else '').replace('__MAIN__',main)
with tempfile.TemporaryDirectory(prefix='mantech-mailbox-faction-') as tmp:
 folder=Path(tmp);(folder/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=folder,check=True)
 subprocess.run([str(folder/'test.exe')],check=True)
