"""Exercise the actual core cooldown writer, including Portable Bank and native exclusions."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/game/Spells/Spell.cpp').read_text()
start=source.index('void Spell::SendSpellCooldown()');brace=source.index('{',start);depth=0
for end in range(brace,len(source)):
    depth+=(source[end]=='{')-(source[end]=='}')
    if not depth:break
method=source[start:end+1]
code=r"""
#include <cassert>
#include <cstdint>
#include <vector>
#include <iostream>
using uint32=uint32_t;using uint8=uint8_t;
enum{TYPEID_PLAYER=4,SPELL_ATTR_PASSIVE=1,SPELL_ATTR_COOLDOWN_ON_EVENT=2,SMSG_SPELL_COOLDOWN=3,SPELL_COOLDOWN_FLAG_NONE=0,ITEM_CLASS_CONSUMABLE=0,ITEM_SUBCLASS_POTION=1};
enum class SpellCategoryFlags{CooldownEventOnLeaveCombat=1};
struct SpellCategoryEntry{unsigned flags=1;};
struct Store{SpellCategoryEntry entry;SpellCategoryEntry const* LookupEntry(unsigned){return &entry;}}sSpellCategory;
struct SpellEntry{unsigned Id=7977,Category=0;bool passive=false,event=true;bool HasAttribute(unsigned flag)const{return flag==SPELL_ATTR_PASSIVE?passive:event;}};
struct ItemSpell{unsigned SpellId=7977;int SpellCooldown=1800000;unsigned SpellCategory=0;};
struct ItemPrototype{ItemSpell Spells[1];unsigned Class=1,SubClass=0,ItemId=65004;};
struct Item{unsigned entry=65004;ItemPrototype proto;unsigned GetEntry(){return entry;}ItemPrototype const*GetProto(){return &proto;}};
struct WorldPacket{std::vector<uint64_t>words;WorldPacket(unsigned opcode,unsigned){assert(opcode==SMSG_SPELL_COOLDOWN);}template<class T>WorldPacket&operator<<(T v){words.push_back(v);return *this;}};
struct Session{std::vector<uint64_t>words;void SendPacket(WorldPacket const*p){words=p->words;}void SendPacket(WorldPacket const&p){words=p.words;}};
struct Player{unsigned type=TYPEID_PLAYER,adds=0;bool held=false;ItemPrototype const*item=nullptr;Session session;
 bool IsPlayer(){return type==TYPEID_PLAYER;}unsigned GetTypeId(){return type;}uint64_t GetObjectGuid(){return 91;}
 void SetLastPotionId(unsigned){}void SetCooldownEventOnLeaveCombatSpellId(unsigned){}
 void AddCooldown(SpellEntry const&,ItemPrototype const*p,bool hold){++adds;item=p;held=hold;}
 Session*GetSession(){return &session;}
};
struct Spell{SpellEntry*m_spellInfo;Item*m_CastItem;Player*m_trueCaster;Player*m_caster;bool m_channelOnly=false;
 ItemPrototype const*GetCooldownItemPrototype(){return m_CastItem?m_CastItem->GetProto():nullptr;}void SendSpellCooldown();};
__METHOD__
int main(){
 Player p;Item item;SpellEntry info;Spell spell{&info,&item,&p,&p};
 for(unsigned id:{65000u,65001u,65002u,65004u}){
  item.entry=id;p.session.words.clear();spell.SendSpellCooldown();assert(!p.held&&p.item==&item.proto);
  assert(p.session.words.size()==__WORDS__);assert(p.session.words.front()==91);assert(p.session.words[p.session.words.size()-2]==7977&&p.session.words.back()==1800000);
 }
 // A second use after expiry gets the same authoritative timer packet.
 item.entry=65004;p.session.words.clear();spell.SendSpellCooldown();assert(p.session.words.back()==1800000&&!p.held);
 for(unsigned id:{65003u,6948u}){item.entry=id;p.session.words.clear();spell.SendSpellCooldown();assert(p.held&&p.session.words.empty());}
 spell.m_CastItem=nullptr;spell.SendSpellCooldown();assert(!p.item&&p.held&&p.session.words.empty());spell.m_CastItem=&item;item.entry=65004;
 unsigned before=p.adds;info.passive=true;spell.SendSpellCooldown();assert(p.adds==before);info.passive=false;
 spell.m_channelOnly=true;spell.SendSpellCooldown();assert(p.adds==before);spell.m_channelOnly=false;
 p.type=3;spell.SendSpellCooldown();assert(p.session.words.empty());p.type=TYPEID_PLAYER;
 item.proto.Spells[0].SpellCooldown=0;spell.SendSpellCooldown();assert(p.session.words.empty());
 item.proto.Spells[0].SpellCooldown=1800000;item.proto.Spells[0].SpellId=999;spell.SendSpellCooldown();assert(p.session.words.empty());
 std::cout<<"PASS real cooldown writer: repeat bank timer, persistent item cooldown, era packet layout and native exclusions\n";
}
""".replace('__METHOD__',method).replace('__WORDS__','4' if 'uint8(SPELL_COOLDOWN_FLAG_NONE)' in method else '3')
with tempfile.TemporaryDirectory(prefix='mantech-bank-cooldown-') as tmp:
    tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl.exe','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],check=True)
