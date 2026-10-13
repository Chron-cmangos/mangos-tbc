"""Exercise the native ground endpoint projection without a running realm."""
from pathlib import Path
import os, subprocess, sys, tempfile, shutil
root=Path(sys.argv[1])
source=(root/'src/game/MotionGenerators/PathFinder.cpp').read_text()
start=source.index('void PathFinder::AdjustGroundPathEndpoint(')
end=source.index('void PathFinder::BuildPolyPath(',start)
method=source[start:end]
skipstart=source.index('bool PathFinder::CanSkipPathPoint(')
skipend=source.index('void PathFinder::NormalizePath()',skipstart)
skipmethod=source[skipstart:skipend]
poly=source[end:source.index('void PathFinder::BuildPointPath(',end)]
assert poly.index('AdjustGroundPathEndpoint(endPoint, endPoly)') < poly.index('if (startPoly == endPoly)')
same=poly[poly.index('if (startPoly == endPoly)'):poly.index('// look for startPoly/endPoly')]
assert 'BuildPointPath(startPoint, endPoint)' in same and '!m_sourceUnit->CanFly()' in same
assert 'setEndPosition(Vector3(endPoint[2], endPoint[0], endPoint[1]))' in poly
formation=(root/'src/game/MotionGenerators/TargetedMovementGenerator.cpp').read_text()
formation=formation[formation.index('float FormationMovementGenerator::BuildPath('):formation.index('// return true if follower')]
assert 'i_path->calculate(ownerPos, nextPos)' in formation
assert 'i_path->calculate(path.back(), nextPos)' in formation
assert 'i_path->calculate(path.back(), nextPos, true' not in formation
assert 'i_path->getPath().push_back(path.back())' in formation
code=r"""
#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
using dtPolyRef=unsigned long long;
constexpr int NAV_GROUND=1,VERTEX_SIZE=3;
bool dtStatusFailed(int s){return s!=0;}
struct dtMeshTile{};
struct dtPoly{int flags=NAV_GROUND;};
struct Mesh{
 dtMeshTile tile;dtPoly polygon;bool fail=false;
 int getTileAndPolyByRef(dtPolyRef,const dtMeshTile** t,const dtPoly** p){*t=&tile;*p=&polygon;return fail;}
};
struct Query{
 bool fail=false,over=true;float height=-181.915863f;int calls=0;
 int closestPointOnPoly(dtPolyRef,const float* point,float* surface,bool* o){
  ++calls;surface[0]=point[0];surface[1]=height;surface[2]=point[2];*o=over;return fail;
 }
};
struct Unit{
 bool transport=false,fly=false,water=false,hover=false;mutable int corrections=0;
 bool GetTransport()const{return transport;} bool CanFly()const{return fly;}
 bool IsInWater()const{return water;}bool HasHoverAura()const{return hover;}
 void UpdateAllowedPositionZ(float x,float y,float& z)const{
  assert(x==958.743652f&&y==-937.120789f);assert(z==-181.915863f);
  ++corrections;z=-181.829636f;
 }
};
struct PathFinder{
 Unit* m_sourceUnit;bool m_ignoreNormalization=false;Mesh* m_navMesh;Query* m_navMeshQuery;
 void AdjustGroundPathEndpoint(float*,dtPolyRef);
};
struct Vector3 {
 float x,y,z;Vector3 operator-(Vector3 p)const{return {x-p.x,y-p.y,z-p.z};}
 Vector3 operator+(Vector3 p)const{return {x+p.x,y+p.y,z+p.z};}
 Vector3 operator*(float f)const{return {x*f,y*f,z*f};}
 float dot(Vector3 p)const{return x*p.x+y*p.y+z*p.z;}
 float squaredMagnitude()const{return dot(*this);}
};
constexpr float LINE_FAULT=0.5f;
struct Optimizer{bool CanSkipPathPoint(const Vector3&,const Vector3&,const Vector3&)const;};
#define DEBUG_FILTER_LOG(...) ((void)0)
constexpr int PATHFIND_NORMAL=1,PATHFIND_SHORTCUT=2,PATHFIND_INCOMPLETE=4,PATHFIND_NOPATH=8;
struct PolygonPath {
 Unit* m_sourceUnit;bool m_ignoreNormalization=false;int m_type=0,m_polyLength=0,points=0,shortcuts=0;
 bool pointFailure=false;dtPolyRef m_pathPolyRefs[2];
 void BuildPointPath(float*,float*){++points;if(pointFailure)m_type=PATHFIND_NOPATH;}
 void BuildShortcut(){++shortcuts;m_type=PATHFIND_SHORTCUT;}
 void Run(bool farFromPoly=false){dtPolyRef startPoly=1,endPoly=1;float startPoint[3]={},endPoint[3]={};
"""+same+r"""
 }
};
"""+method+skipmethod.replace('PathFinder::CanSkipPathPoint','Optimizer::CanSkipPathPoint')+r"""
int main(){
 Unit unit;Mesh mesh;Query query;PathFinder path{&unit,false,&mesh,&query};
 auto run=[&](bool corrected){float p[]={-937.120789f,-184.229004f,958.743652f};
  int before=unit.corrections;path.AdjustGroundPathEndpoint(p,1);
  assert(p[0]==-937.120789f&&p[2]==958.743652f);
  assert(p[1]==(corrected?-181.829636f:-184.229004f));
  assert(unit.corrections==before+int(corrected));
 };
 run(true);
 for(bool* flag:{&unit.transport,&unit.fly,&unit.water,&unit.hover,&path.m_ignoreNormalization}){
  *flag=true;run(false);*flag=false;
 }
 path.m_sourceUnit=nullptr;run(false);path.m_sourceUnit=&unit;
 mesh.fail=true;run(false);mesh.fail=false;
 mesh.polygon.flags=4;run(false);mesh.polygon.flags=NAV_GROUND;
 query.fail=true;run(false);query.fail=false;
 query.over=false;run(false);query.over=true;
 query.height=-150.f;run(false);query.height=-181.915863f;run(true);
 Optimizer optimizer;
 assert(optimizer.CanSkipPathPoint({0,0,0},{1,0,0},{2,0,0}));
 assert(optimizer.CanSkipPathPoint({0,0,0},{1,0,1},{2,0,2}));
 assert(!optimizer.CanSkipPathPoint({0,0,0},{1,0,2.4f},{2,0,0}));
 assert(!optimizer.CanSkipPathPoint({0,0,0},{1,0,-2.4f},{2,0,0}));
 assert(!optimizer.CanSkipPathPoint({0,0,0},{1,2,0},{2,0,0}));
 assert(!optimizer.CanSkipPathPoint({0,0,0},{3,0,0},{2,0,0}));
 assert(!optimizer.CanSkipPathPoint({0,0,0},{1,0,0},{0,0,0}));
 assert(!optimizer.CanSkipPathPoint({958,-937,-184},{959,-937,-181.8f},{960,-937,-184}));
 {PolygonPath same{&unit};same.Run();assert(same.m_type==PATHFIND_NORMAL&&same.points==1&&!same.shortcuts);
  same.pointFailure=true;same.Run();assert(same.m_type==PATHFIND_NOPATH);}
 for(bool* flag:{&unit.transport,&unit.fly,&unit.water,&unit.hover}){
  *flag=true;PolygonPath same{&unit};same.Run();assert(same.m_type==PATHFIND_NORMAL&&same.shortcuts==1&&!same.points);
  same.Run(true);assert(same.m_type==PATHFIND_INCOMPLETE);*flag=false;
 }
 {PolygonPath same{nullptr};same.Run();assert(same.m_type==PATHFIND_NORMAL&&same.shortcuts==1);}
 {PolygonPath same{&unit};same.m_ignoreNormalization=true;same.Run();assert(same.m_type==PATHFIND_NORMAL&&same.shortcuts==1);}
 puts("PASS native ground endpoint: buried coordinates, floor correction, liquid/flying/hover/transport, invalid and remote polygons");
 puts("PASS native path optimizer: hills, valleys, horizontal corners, backtracking, duplicate endpoints and translated coordinates");
 puts("PASS native same-polygon dispatch: ground smoothing, failed paths, airborne/liquid/transport and map-only status preservation");
}
"""
with tempfile.TemporaryDirectory(prefix='mantech-ground-path-') as tmp:
 tmp=Path(tmp);file=tmp/'test.cpp';file.write_text(code)
 if shutil.which('cl'):
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',str(file),'/Fe:'+str(tmp/'test.exe')],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
 else:
  subprocess.run(['c++','-std=c++17',str(file),'-o',str(tmp/'test')],check=True)
  subprocess.run([str(tmp/'test')],check=True)
