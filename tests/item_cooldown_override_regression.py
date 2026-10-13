from pathlib import Path
import subprocess,tempfile,sys
r=Path(sys.argv[1]);s=(r/'src/game/Entities/Player.cpp').read_text()
start=s.index('static bool RetiredEternalQuintessenceCooldown(')
end=s.index('\nvoid Player::_LoadSpellCooldowns',start)
body=s[start:end]
assert 'if (RetiredEternalQuintessenceCooldown(spell_id, item_id, itemProto))' in s
assert 'SendItemQuerySingleResponse(22754)' in s
code="""#include <cassert>
#include <iostream>
using uint32=unsigned;struct ItemPrototype{struct Spell{uint32 SpellId=21358;int SpellCooldown=0,SpellCategoryCooldown=0;};Spell Spells[5];};
"""+body+"""
int main(){ItemPrototype item;assert(RetiredEternalQuintessenceCooldown(21358,22754,&item));
assert(!RetiredEternalQuintessenceCooldown(21358,17333,&item));assert(!RetiredEternalQuintessenceCooldown(42,22754,&item));assert(!RetiredEternalQuintessenceCooldown(21358,22754,nullptr));
for(auto&s:item.Spells){s.SpellCooldown=3600000;s.SpellCategoryCooldown=3600000;}assert(!RetiredEternalQuintessenceCooldown(21358,22754,&item));
for(auto&s:item.Spells){s.SpellCooldown=0;s.SpellCategoryCooldown=3600000;}assert(!RetiredEternalQuintessenceCooldown(21358,22754,&item));
for(auto&s:item.Spells){s.SpellCooldown=-1;s.SpellCategoryCooldown=-1;}assert(!RetiredEternalQuintessenceCooldown(21358,22754,&item));
std::cout<<"PASS Eternal explicit-zero cooldown retirement; Aqual, unrelated, default and category cooldowns preserved\\n";}
"""
with tempfile.TemporaryDirectory(prefix='mantech-eternal-') as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
