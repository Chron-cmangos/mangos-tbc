"""Compile actual production method bodies against focused lifecycle/packet/file fixtures."""
from pathlib import Path
import subprocess,tempfile,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
def method(file,signature):
    s=(root/file).read_text();a=s.index(signature);b=s.index('{',a);depth=1;i=b+1
    while depth:
        depth += (s[i]=='{')-(s[i]=='}');i+=1
    return s[a:i]
code=r'''
#include <cassert>
#include <cstdio>
#include <ctime>
#include <map>
#include <list>
#include <vector>
#include <string>
#include <filesystem>
#include <fstream>
#include <chrono>
#include <algorithm>
#include <cstdint>
using uint32=uint32_t; using int32=int32_t;
struct ObjectGuid {};
struct GameObject {bool owner=true,deleted=false;int respawn=10;uint32 spell=1;
 void SetOwnerGuid(ObjectGuid){owner=false;} void SetRespawnTime(int n){respawn=n;}
 uint32 GetSpellId(){return spell;} void Delete(){assert(!owner);assert(!respawn);deleted=true;}};
using GameObjectList=std::list<GameObject*>;
struct Unit {GameObjectList m_gameObj,m_wildGameObjs;
 void RemoveGameObject(uint32,bool);void RemoveAllGameObjects();};
struct WorldPacket {int id;};
struct WorldSession {bool socket;std::vector<int> sent;bool HasClientSocket(){return socket;}void SendPacket(WorldPacket p,bool=false){sent.push_back(p.id);}};
struct UpdateData {int builds=0;std::vector<WorldPacket> m_afterCreatePacket{{77}};
 bool HasData(){return true;}size_t GetPacketCount(){return 2;}WorldPacket BuildPacket(size_t i){++builds;return {int(i)};}void SendData(WorldSession&);};
namespace MaNGOS {namespace Filesystem {
 using std::filesystem::path;using std::filesystem::directory_iterator;
 using std::filesystem::file_size;using std::filesystem::rename;using std::filesystem::remove;using std::filesystem::is_regular_file;
 time_t last_write_time(path const& p){return std::chrono::system_clock::to_time_t(std::chrono::system_clock::now()+std::chrono::duration_cast<std::chrono::system_clock::duration>(std::filesystem::last_write_time(p)-std::filesystem::file_time_type::clock::now()));}
}}
struct Config {bool enabled=true,daily=true;bool GetBoolDefault(const char* key,bool){return std::string(key)=="LogRotation.Enabled"?enabled:daily;}int GetIntDefault(const char* key,int){return std::string(key)=="LogRotation.RetentionDays"?14:1;}} sConfig;
struct Log {FILE *logfile=nullptr,*gmLogfile=nullptr,*charLogfile=nullptr,*dberLogfile=nullptr,*eventAiErLogfile=nullptr,*scriptErrLogFile=nullptr,*raLogfile=nullptr,*worldLogfile=nullptr,*customLogFile=nullptr,*performanceLogFile=nullptr;
 time_t m_nextRotationCheck=0;std::map<FILE*,std::pair<std::string,int>> m_rotationFiles;
 std::string GetTimestampStr(){return "fixture";}void RotateLogFilesIfNeeded();};
'''
code+=method('src/game/Entities/Unit.cpp','void Unit::RemoveGameObject(uint32')+'\n'
code+=method('src/game/Entities/Unit.cpp','void Unit::RemoveAllGameObjects()')+'\n'
send=method('src/game/Entities/UpdateData.cpp','void UpdateData::SendData(')
if 'bool forceSend' in send:code=code.replace('void SendData(WorldSession&);','void SendData(WorldSession&,bool=false);')
code+=send+'\n'+method('src/shared/Log/Log.cpp','void Log::RotateLogFilesIfNeeded()')
code+=r'''
int main(){
 GameObject owned,wild;Unit u;u.m_gameObj.push_back(&owned);u.m_wildGameObjs.push_back(&wild);
 u.RemoveAllGameObjects();assert(owned.deleted&&!owned.owner&&u.m_gameObj.empty());assert(!wild.deleted&&wild.owner&&u.m_wildGameObjs.empty());u.RemoveAllGameObjects();
 UpdateData human,bot;WorldSession h{true},b{false};human.SendData(h);bot.SendData(b);assert(human.builds==2);
#ifdef ENABLE_PLAYERBOTS
 assert(bot.builds==0);
#else
 assert(bot.builds==2);
#endif
 AFTER_CREATE_ASSERT
 Log log;auto p=std::filesystem::absolute("runtime.log");auto name=p.string();
 log.logfile=fopen(name.c_str(),"a");assert(log.logfile);log.m_rotationFiles[log.logfile]={name,-1};
 fputs("before rotation\n",log.logfile);fflush(log.logfile);
 std::ofstream("runtime.log.old.archive")<<"expired";std::ofstream("unrelated.old.archive")<<"keep";
 std::filesystem::last_write_time("runtime.log.old.archive",std::filesystem::file_time_type::clock::now()-std::chrono::hours(24*20));
 log.RotateLogFilesIfNeeded();assert(log.logfile);assert(std::filesystem::exists("runtime.log.fixture.archive"));assert(!std::filesystem::exists("runtime.log.old.archive"));assert(std::filesystem::exists("unrelated.old.archive"));
 std::ifstream archived("runtime.log.fixture.archive");std::string text;std::getline(archived,text);assert(text=="before rotation");archived.close();
 fputs("after rotation\n",log.logfile);fflush(log.logfile);assert(std::filesystem::file_size(p)>0);
 std::filesystem::remove("runtime.log.fixture.archive");
 sConfig.daily=false;std::string large(1024*1024,'x');fwrite(large.data(),1,large.size(),log.logfile);fflush(log.logfile);log.m_nextRotationCheck=0;
 log.RotateLogFilesIfNeeded();assert(std::filesystem::file_size("runtime.log.fixture.archive")>=1024*1024);assert(log.logfile);
 std::filesystem::remove("runtime.log.fixture.archive");sConfig.enabled=false;log.m_rotationFiles[log.logfile].second=-1;log.m_nextRotationCheck=0;
 log.RotateLogFilesIfNeeded();assert(!std::filesystem::exists("runtime.log.fixture.archive"));fclose(log.logfile);
}
'''.replace('AFTER_CREATE_ASSERT','assert(h.sent.back()==77&&b.sent.back()==77);' if 'm_afterCreatePacket' in send else 'assert(h.sent.size()==2);')
with tempfile.TemporaryDirectory(prefix='core-log-regression-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(code)
    for bots in (True,False):
        cmd=['cl','/nologo','/std:c++20','/EHsc','test.cpp','/Fe:test.exe']+(['/DENABLE_PLAYERBOTS'] if bots else [])
        result=subprocess.run(cmd,cwd=p,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        run=p/('bots' if bots else 'humans');run.mkdir();subprocess.run([str(p/'test.exe')],cwd=run,check=True)
print(root.name+': owned-object lifecycle, socket-aware packets, daily/size rotation, archive retention passed (bots enabled/disabled)')
