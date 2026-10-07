"""Exercise actual cleanup SQL and compiled event registration against isolated fixtures."""
from pathlib import Path
import argparse, re, sqlite3, subprocess, tempfile
from instance_spawn_regression import block

parser=argparse.ArgumentParser()
parser.add_argument('--before-dir',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]/'src/game'
def read(rel):
    return (args.before_dir/Path(rel).name if args.before_dir else root/rel).read_text()

count=failed=0
def check(ok,name):
    global count,failed
    count+=1
    if not ok:
        failed+=1
        print('FAIL: '+name)

constants={name:int(value,16) for name,value in re.findall(r'(MAP[01]_\w+)\s*=\s*(0x[0-9A-Fa-f]+)',read('Maps/MapManager.h'))}
assert len(constants)==13
cleanup=block(read('Maps/MapPersistentStateMgr.cpp'),'void MapPersistentStateManager::CleanupInstances(')
for table in ('creature_respawn','gameobject_respawn'):
    match=re.search(r'CharacterDatabase\.(?:PExecute|Execute)\("(DELETE FROM '+table+r'[^"\n]+)"([^;]*);',cleanup)
    assert match
    sql=match[1]
    if '%u' in sql:
        values=[constants[key] for key in re.findall(r'uint32\((MAP[01]_\w+)\)',match[2])]
        assert len(values)==4
        sql=sql % tuple(values)
    db=sqlite3.connect(':memory:')
    db.execute('CREATE TABLE instance(id INTEGER PRIMARY KEY)')
    db.execute('INSERT INTO instance VALUES(98)')
    db.execute('CREATE TABLE '+table+'(guid INTEGER, instance INTEGER)')
    ids=[0,98,99,*constants.values(),0xFFF000,0xFFF007,0xFFF010,0xFFF018]
    db.executemany('INSERT INTO '+table+' VALUES(?,?)',enumerate(ids))
    db.execute(sql)
    survivors={row[0] for row in db.execute('SELECT instance FROM '+table)}
    for value in ids:
        expected=value in (0,98) or value in constants.values()
        check((value in survivors)==expected,f'{table}: {value:#x} preserved={expected}')
    db.close()

events=read('GameEvents/GameEventMgr.cpp')
kind=re.search(r'AddEventGuid\(goDbGuid, (HIGHGUID_\w+)\)',block(events,'void GameEventMgr::GameEventSpawn('))[1]
remove_kind=re.search(r'RemoveEventGuid\(goDbGuid, (HIGHGUID_\w+)\)',block(events,'void GameEventMgr::GameEventUnspawn('))[1]
manager=read('Maps/SpawnManager.cpp')
methods='\n'.join(block(manager,m) for m in ('void SpawnManager::AddEventGuid(', 'void SpawnManager::RemoveEventGuid(', 'bool SpawnManager::IsEventGuid('))
code='''#include <set>
#include <iostream>
using uint32=unsigned;enum HighGuid{HIGHGUID_UNIT,HIGHGUID_GAMEOBJECT};
struct SpawnManager {std::set<uint32> m_eventGoDbGuids,m_eventCreatureDbGuids;
void AddEventGuid(uint32,HighGuid);void RemoveEventGuid(uint32,HighGuid);bool IsEventGuid(uint32,HighGuid)const;};
'''+methods+'''
int main(){SpawnManager s;int failed=0;
auto check=[&](bool ok){if(!ok)++failed;};
s.AddEventGuid(12345, '''+kind+''');
check(s.IsEventGuid(12345,HIGHGUID_GAMEOBJECT));
check(!s.IsEventGuid(12345,HIGHGUID_UNIT));
s.RemoveEventGuid(12345, '''+remove_kind+''');
check(!s.IsEventGuid(12345,HIGHGUID_GAMEOBJECT));
check(!s.IsEventGuid(12345,HIGHGUID_UNIT));
// Same low GUID can independently belong to a real event creature.
s.AddEventGuid(12345,HIGHGUID_UNIT);s.AddEventGuid(12345, '''+kind+''');
s.RemoveEventGuid(12345, '''+remove_kind+''');
check(s.IsEventGuid(12345,HIGHGUID_UNIT));
std::cout<<5-failed<<"/5 event checks passed\\n";return failed;}
'''
with tempfile.TemporaryDirectory() as temp:
    folder=Path(temp);cpp=folder/'test.cpp';exe=folder/'test.exe';cpp.write_text(code)
    result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17',str(cpp),'/Fe:'+str(exe)],cwd=folder,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    result=subprocess.run([str(exe)],capture_output=True,text=True)
    print(result.stdout,end='')
    count+=5;failed+=result.returncode
print(f'{count-failed}/{count} overlap checks passed')
raise SystemExit(bool(failed))
