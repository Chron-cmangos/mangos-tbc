"""Compile actual pool/event/respawn guards. Optional --before-dir proves old failures."""
from pathlib import Path
import argparse, subprocess, tempfile, json, re

def block(text, marker):
    start=text.index(marker); opening=text.index('{',start); depth=0
    for end in range(opening,len(text)):
        depth+=(text[end]=='{')-(text[end]=='}')
        if not depth: return text[start:end+1]
    raise AssertionError(marker)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--before-dir',type=Path);args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    def read(rel):
        return ((args.before_dir/Path(rel).name) if args.before_dir else (root/'src/game'/rel)).read_text()
    pools=read('Pools/PoolManager.cpp');header=read('Pools/PoolManager.h')
    if 'bool PoolTemplateData::CanBeSpawnedAtMap(' in pools:
        method=block(pools,'bool PoolTemplateData::CanBeSpawnedAtMap(')
        declaration='bool CanBeSpawnedAtMap(MapEntry const*,uint32) const;'
    else:
        method='';declaration=block(header,'bool CanBeSpawnedAtMap(')
    tests=[];methods=[]
    for i,marker in enumerate(('void PoolGroup<Creature>::Despawn1Object(', 'void PoolGroup<GameObject>::Despawn1Object(',
            'void PoolGroup<Creature>::ReSpawn1Object(', 'void PoolGroup<GameObject>::ReSpawn1Object(')):
        body=block(pools,marker)
        condition=re.search(r'if \((mapState.GetMapId\(\).*?)\)\s*return;',body).group(1)
        methods.append(f'bool pool{i}(State& mapState,Data* data) {{ return !({condition}); }}')
        tests.append(f'check(pool{i}(dungeon,&smData),"pool operation {i}: dungeon"); check(!pool{i}(otherDungeon,&smData),"pool operation {i}: wrong map"); check(pool{i}(partition,&worldData),"pool operation {i}: own partition"); check(!pool{i}(otherPartition,&worldData),"pool operation {i}: other partition");')
    events=read('GameEvents/GameEventMgr.cpp')
    conditions=re.findall(r'if \(([^\n]*sMapMgr.GetContinentInstanceId\(data->mapid, data->posX, data->posY\)[^\n]*)\)\s*continue;',events)
    assert len(conditions)==4
    for i,condition in enumerate(conditions):
        methods.append(f'bool event{i}(State* map,Data* data) {{ return !({condition}); }}')
        tests.append(f'check(event{i}(&dungeon,&smData),"event operation {i}: dungeon");check(event{i}(&partition,&worldData),"event operation {i}: own partition");check(!event{i}(&otherPartition,&worldData),"event operation {i}: other partition");')
    respawns=read('Maps/MapPersistentStateMgr.cpp')
    for i,name in enumerate(('LoadCreatureRespawnTimes','LoadGameobjectRespawnTimes')):
        body=block(respawns,'void MapPersistentStateManager::'+name+'(')
        start=body.index('        if (!mapEntry->Instanceable()');end=body.index('        MapPersistentState* state',start)
        guard=body[start:end].replace('continue;','return false;')
        methods.append(f'bool respawn{i}(MapEntry const* mapEntry,Data* data,uint32 mapId,uint32 instanceId,unsigned difficulty=0){{'+guard+'return true;}')
        tests.append(f'check(respawn{i}(&kalimdor,&worldData,0,0),"respawn {i}: world null join");check(respawn{i}(&sm,&smData,189,98),"respawn {i}: valid dungeon");check(!respawn{i}(&sm,&smData,33,98),"respawn {i}: wrong saved map");check(!respawn{i}(&sm,&smData,189,0),"respawn {i}: missing dungeon save");')
    code='''#include <iostream>
using uint32=unsigned;
enum {REGULAR_DIFFICULTY=0,MAX_DIFFICULTY=2,MAX_RAID_DIFFICULTY=4,MAX_DUNGEON_DIFFICULTY=2};
struct MapEntry {uint32 id;bool instanced;bool Instanceable()const{return instanced;}bool IsRaid()const{return false;}};
struct Data {uint32 mapid;float posX=0,posY=0;};
struct State {MapEntry* entry;uint32 instance;uint32 GetMapId(){return entry->id;} uint32 GetInstanceId(){return instance;} MapEntry* GetMapEntry(){return entry;}bool Instanceable(){return entry->Instanceable();}};
struct Manager {uint32 GetContinentInstanceId(uint32 id,float,float){return id<=1?3:0;}}sMapMgr;
struct PoolTemplateData {MapEntry const* mapEntry=nullptr;uint32 instanceId=0;
'''+declaration+'\n};\n'+method+'\n'+'\n'.join(methods)+'''
int main(){int failed=0;int count=0;auto check=[&](bool ok,const char* name){++count;if(!ok){++failed;std::cout<<"FAIL: "<<name<<"\\n";}};
MapEntry sm{189,true},other{33,true},kalimdor{1,false};Data smData{189},worldData{1};
State dungeon{&sm,98},otherDungeon{&other,98},partition{&kalimdor,3},otherPartition{&kalimdor,4};
PoolTemplateData p;p.mapEntry=&sm;
check(p.CanBeSpawnedAtMap(&sm,98),"pool admission: SM copy 98");
check(p.CanBeSpawnedAtMap(&sm,99),"pool admission: independent SM copy 99");
check(!p.CanBeSpawnedAtMap(&other,98),"pool admission: wrong map");
check(!p.CanBeSpawnedAtMap(nullptr,98),"pool admission: null destination");
p.mapEntry=nullptr;check(!p.CanBeSpawnedAtMap(&sm,98),"pool admission: unassigned");
p.mapEntry=&kalimdor;p.instanceId=3;
check(p.CanBeSpawnedAtMap(&kalimdor,3),"pool admission: own world partition");
check(!p.CanBeSpawnedAtMap(&kalimdor,4),"pool admission: other world partition");
'''+ '\n'.join(tests)+'''
std::cout<<count-failed<<"/"<<count<<" checks passed\\n";return failed?1:0;}
'''
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);cpp=tmp/'test.cpp';exe=tmp/'test.exe';cpp.write_text(code)
        compiled=subprocess.run(['cl','/nologo','/EHsc','/std:c++17',str(cpp),'/Fe:'+str(exe)],cwd=tmp,capture_output=True,text=True)
        if compiled.returncode:raise RuntimeError(compiled.stdout+compiled.stderr)
        run=subprocess.run([str(exe)],capture_output=True,text=True)
        print(run.stdout,end='');raise SystemExit(run.returncode)
if __name__=='__main__':main()
