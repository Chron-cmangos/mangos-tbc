"""Exercise the production area-height lookup before navigation initialization."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'src/game/Maps/GridMap.cpp').read_text()
a=s.index('bool TerrainInfo::GetAreaInfo(');b=s.index('{',a);depth=1;i=b+1
while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
method=s[a:i]
assert 'GetGrid(x, y, true)' in method
prefix=r"""
#include <cassert>
#include <cstdint>
#include <stdexcept>
using uint32=uint32_t;using int32=int32_t;
struct GridMap {float height=0;float getHeight(float,float){return height;}};
struct VMap {bool found=true;float floor=0;int calls=0;
 bool getAreaInfo(uint32,float,float,float& z,uint32& flags,int32& adt,int32& root,int32& group){
  ++calls;if(!found)return false;z=floor;flags=42;adt=1;root=2;group=3;return true;}};
struct TerrainInfo {
 VMap vmap;VMap* m_vmgr=&vmap;GridMap grid;bool navigationReady=false,missingGrid=false;int gridCalls=0,fullLoads=0;
 uint32 GetMapId()const{return 530;}
 GridMap* GetGrid(float,float,bool mapOnly=false){
  ++gridCalls;
  if(!mapOnly){++fullLoads;if(!navigationReady)throw std::logic_error("MMapManager::loadMap requires initialized navigation");}
  return missingGrid?nullptr:&grid;
 }
 bool GetAreaInfo(float,float,float,uint32&,int32&,int32&,int32&)const;
};
"""
checks=r"""
int main(){
 TerrainInfo terrain;uint32 flags=0;int32 adt=0,root=0,group=0;
 auto query=[&](float z){return terrain.GetAreaInfo(1,2,z,flags,adt,root,group);};
#ifdef LEGACY
 bool reproduced=false;try{query(10);}catch(const std::logic_error&){reproduced=true;}
 assert(reproduced&&terrain.fullLoads==1);return 0;
#else
 assert(query(10));assert(terrain.gridCalls==1&&terrain.fullLoads==0);
 assert(flags==42&&adt==1&&root==2&&group==3);
 terrain.grid.height=5;assert(!query(10)); // terrain occludes the lower WMO floor
 terrain.grid.height=12;assert(query(10)); // unchanged strict height boundary
 terrain.grid.height=13;assert(query(10));
 terrain.vmap.floor=5;terrain.grid.height=5;assert(query(10));
 terrain.missingGrid=true;assert(query(10));
 terrain.vmap.found=false;int calls=terrain.gridCalls;assert(!query(10));assert(calls==terrain.gridCalls);
 terrain.missingGrid=false;terrain.vmap.found=true;terrain.navigationReady=true;assert(query(10));
 assert(terrain.fullLoads==0);
#endif
}
"""
with tempfile.TemporaryDirectory(prefix='terrain-area-startup-') as temp:
 p=Path(temp)
 for legacy in (True,False):
  body=method.replace('GetGrid(x, y, true)','GetGrid(x, y)') if legacy else method
  (p/'test.cpp').write_text(prefix+body+checks)
  args=['cl','/nologo','/std:c++20','/EHsc','test.cpp','/Fe:test.exe']
  if legacy:args.append('/DLEGACY')
  result=subprocess.run(args,cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('Terrain area startup: legacy navigation failure reproduced; map-only lookup, height filtering and missing-data cases passed')
