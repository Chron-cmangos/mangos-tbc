"""Execute native malformed-header rejection without allocating packet bodies."""
from pathlib import Path
import subprocess,sys,tempfile
r=Path(sys.argv[1]);source=(r/'src/game/Server/WorldSocket.cpp').read_text()
start=source.index('        if ((header->size < 4)');end=source.index('\n        const Opcodes opcode',start)
branch=source[start:end]
code=r'''
#include <cassert>
#include <string>
#include <iostream>
#include <utility>
constexpr unsigned NUM_MSG_TYPES=1400;
struct Header{unsigned size,cmd;};struct Socket{bool closed=false;void Close(){closed=true;}std::string GetRemoteEndpoint(){return "127.0.0.1:12345";}};
struct Log{unsigned reports=0;template<class...T>void outError(const char*,T...){++reports;}}sLog;
void ReadHeader(Socket*self,Header*header){__BRANCH__ assert(!self->closed);}
int main(){for(auto pair:{std::pair<unsigned,unsigned>{3,1},{0,1},{0x2801,1},{10,NUM_MSG_TYPES},{18245,539959380},{5635,32374785},{8,999999}}){
 Socket s;Header h{pair.first,pair.second};unsigned before=sLog.reports;ReadHeader(&s,&h);assert(s.closed&&sLog.reports==before+1);}
 for(auto pair:{std::pair<unsigned,unsigned>{4,0},{0x2800,NUM_MSG_TYPES-1},{10,100}}){Socket s;Header h{pair.first,pair.second};unsigned before=sLog.reports;ReadHeader(&s,&h);assert(!s.closed&&sLog.reports==before);}
 std::cout<<"PASS native invalid-header close, HTTP/TLS rejection, boundary-valid WoW headers preserved\n";}
'''.replace('__BRANCH__',branch)
with tempfile.TemporaryDirectory(prefix='mantech-socket-header-') as tmp:
 folder=Path(tmp);(folder/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=folder,check=True)
 subprocess.run([str(folder/'test.exe')],check=True)
