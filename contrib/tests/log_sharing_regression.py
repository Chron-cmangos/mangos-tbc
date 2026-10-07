"""Exercise production log initialization and rotation with real Windows file locks."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
def method(signature):
 s=(root/'src/shared/Log/Log.cpp').read_text();a=s.index(signature);b=s.index('{',a);d=1;i=b+1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
code=r"""
#include <cassert>
#include <cstdio>
#include <ctime>
#include <map>
#include <string>
#include <filesystem>
#include <fstream>
#include <chrono>
#include <algorithm>
#include <cstdint>
#include <mutex>
using uint32=uint32_t;using int32=int32_t;using LogLevel=int;
struct Config {
 std::map<std::string,std::string> strings;std::map<std::string,int> integers;
 bool IsSet(const char* key){return strings.count(key);}
 std::string GetStringDefault(const char* key,const char* d=""){auto i=strings.find(key);return i==strings.end()?d:i->second;}
 int GetIntDefault(const char* key,int d){auto i=integers.find(key);return i==integers.end()?d:i->second;}
 bool GetBoolDefault(const char* key,bool d=false){return GetIntDefault(key,d)!=0;}
} sConfig;
constexpr int LOG_FILTER_COUNT=1;struct Filter{const char* name;const char* configName;bool defaultState;};Filter logFilterData[]={{"","",false}};
namespace MaNGOS {namespace Filesystem {
 using std::filesystem::path;using std::filesystem::directory_iterator;using std::filesystem::exists;
 using std::filesystem::file_size;using std::filesystem::remove;using std::filesystem::is_regular_file;
 int attempts=0;void rename(path const& a,path const& b){++attempts;std::filesystem::rename(a,b);}
 time_t last_write_time(path const& p){return std::chrono::system_clock::to_time_t(std::chrono::system_clock::now()+std::chrono::duration_cast<std::chrono::system_clock::duration>(std::filesystem::last_write_time(p)-std::filesystem::file_time_type::clock::now()));}
}}
struct Log {
 FILE *logfile=nullptr,*gmLogfile=nullptr,*charLogfile=nullptr,*dberLogfile=nullptr,*eventAiErLogfile=nullptr,*scriptErrLogFile=nullptr,*raLogfile=nullptr,*worldLogfile=nullptr,*customLogFile=nullptr,*performanceLogFile=nullptr;
 time_t m_nextRotationCheck=0;std::map<FILE*,std::pair<std::string,int>> m_rotationFiles;std::map<std::string,time_t> m_rotationRetryAfter;
 std::string m_logsDir,m_logsTimestamp,m_gmlog_filename_format;bool m_gmlog_per_account=false,m_includeTime=false,m_charLog_Dump=false;
 int m_logLevel=0,m_logFileLevel=0,m_logFilter=0;std::mutex m_worldLogMtx;
 void InitColors(std::string){}std::string GetTimestampStr(){return "fixture";}
 FILE* openLogFile(char const*,char const*,char const*,char const* = nullptr);
 void CloseLogFiles();void Initialize();void RotateLogFilesIfNeeded();
 ~Log(){CloseLogFiles();}
};
"""
for signature in ('void Log::CloseLogFiles()','void Log::Initialize()','FILE* Log::openLogFile(','void Log::RotateLogFilesIfNeeded()'):
 code+=method(signature)+'\n'
code+=r"""
int main(){
 sConfig.strings["LogFile"]="auth.log";Log auth;auth.Initialize();auth.Initialize();
 assert(!auth.performanceLogFile&&!std::filesystem::exists("Performance.log"));
 auth.CloseLogFiles();std::filesystem::rename("auth.log","auth-closed.log");
 sConfig.strings.clear();sConfig.strings["WorldDatabaseInfo"]="fixture";Log world;world.Initialize();
 assert(world.performanceLogFile&&world.m_rotationFiles.count(world.performanceLogFile));
 world.Initialize();world.CloseLogFiles();std::filesystem::rename("Performance.log","performance-closed.log");
 sConfig.strings["PerformanceLogFile"]="";world.Initialize();assert(!world.performanceLogFile);world.CloseLogFiles();
 sConfig.strings["LogFile"]="locked.log";sConfig.strings["CharLogFile"]="other.log";world.Initialize();
 world.m_rotationFiles[world.logfile].second=-1;world.m_rotationFiles[world.charLogfile].second=-1;
 fputs("before\n",world.logfile);fflush(world.logfile);
 FILE* blocker=fopen("locked.log","a");assert(blocker);int attempts=MaNGOS::Filesystem::attempts;
 world.RotateLogFilesIfNeeded();
 assert(world.logfile&&world.m_rotationRetryAfter.count("locked.log"));
 assert(std::filesystem::exists("other.log.fixture.archive"));assert(MaNGOS::Filesystem::attempts==attempts+2);
 fputs("after failed rotation\n",world.logfile);fflush(world.logfile);
 world.m_nextRotationCheck=0;world.RotateLogFilesIfNeeded();assert(MaNGOS::Filesystem::attempts==attempts+2);
 fclose(blocker);world.m_rotationRetryAfter["locked.log"]=0;world.m_nextRotationCheck=0;world.RotateLogFilesIfNeeded();
 assert(world.logfile&&!world.m_rotationRetryAfter.count("locked.log"));
 std::ifstream archived("locked.log.fixture.archive");std::string content((std::istreambuf_iterator<char>(archived)),{});archived.close();
 assert(content.find("before")!=std::string::npos&&content.find("after failed rotation")!=std::string::npos);
 fputs("after successful rotation\n",world.logfile);fflush(world.logfile);
 world.CloseLogFiles();assert(world.m_rotationFiles.empty()&&world.m_rotationRetryAfter.empty());
 std::filesystem::remove("locked.log.fixture.archive");
 // Size-triggered rotation and suffix-scoped archive retention remain intact.
 sConfig.strings.erase("CharLogFile");sConfig.integers["LogRotation.MaxFileSizeMB"]=1;world.Initialize();
 std::string large(1024*1024,'x');fwrite(large.data(),1,large.size(),world.logfile);fflush(world.logfile);
 std::ofstream("locked.log.expired.archive")<<"old";std::ofstream("unrelated.archive")<<"keep";
 std::filesystem::last_write_time("locked.log.expired.archive",std::filesystem::file_time_type::clock::now()-std::chrono::hours(24*20));
 world.RotateLogFilesIfNeeded();assert(std::filesystem::file_size("locked.log.fixture.archive")>=1024*1024);
 assert(!std::filesystem::exists("locked.log.expired.archive")&&std::filesystem::exists("unrelated.archive"));
}
"""
with tempfile.TemporaryDirectory(prefix='log-sharing-regression-') as temp:
 p=Path(temp);(p/'test.cpp').write_text(code)
 c=subprocess.run(['cl','/nologo','/std:c++20','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if c.returncode:raise RuntimeError(c.stdout+c.stderr)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print(root.name+': auth/world log ownership, reinitialization, real file lock, retry backoff, recovery and retention passed')
