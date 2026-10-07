"""Exercise native prefix matching and dispatch with source teleport registrations.

Run in a C++ compiler environment: python command_dispatch_regression.py <core>
This tests command routing and security, not actual in-game teleportation.
"""
from pathlib import Path
import re, subprocess, sys, tempfile, shutil

root = Path(sys.argv[1])
source = (root / 'src/game/Chat/Chat.cpp').read_text()

def block(marker):
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for end in range(brace, len(source)):
        depth += (source[end] == '{') - (source[end] == '}')
        if not depth:
            return source[start:end + 1]
    raise AssertionError(marker)

tables = '\n'.join(block('static ChatCommand ' + name + '[]') + ';'
                   for name in ('teleCommandTable', 'triggerCommandTable'))
rows = re.findall(r'^\s*\{ "(?:tele|tp|trigger)",[^\n]+', source, re.M)
rows = [row for row in rows if any(name in row for name in ('teleCommandTable', 'triggerCommandTable', 'HandlePlayerTravelCommand'))]
assert len(rows) == 3
tables += '\nChatCommand commands[] = {\n' + '\n'.join(rows) + '\n{nullptr,0,false,nullptr,"",nullptr}};'
handlers = sorted(set(re.findall(r'&ChatHandler::(\w+)', tables)))
cpp = r'''
#include <cassert>
#include <cctype>
#include <cstring>
#include <string>
#include <iostream>
using uint32 = unsigned;
enum {SEC_PLAYER, SEC_MODERATOR, SEC_GAMEMASTER, SEC_ADMINISTRATOR};
enum ChatCommandSearchResult {CHAT_COMMAND_OK,CHAT_COMMAND_UNKNOWN,CHAT_COMMAND_UNKNOWN_SUBCOMMAND};
class ChatHandler;
struct ChatCommand {
 const char* Name; unsigned SecurityLevel; bool AllowConsole;
 bool (ChatHandler::*Handler)(char*); const char* Help; ChatCommand* ChildCommands;
};
class ChatHandler {
public:
 unsigned security = SEC_PLAYER;
 bool isAvailable(const ChatCommand& cmd) const {return security >= cmd.SecurityLevel;}
 bool hasStringAbbr(const char*,const char*) const;
 ChatCommandSearchResult FindCommand(ChatCommand*,const char*&,ChatCommand*&,ChatCommand** = nullptr,std::string* = nullptr,bool = false,bool = false) const;
'''
cpp += '\n'.join('bool ' + name + '(char*) {return true;}' for name in handlers) + '\n};\n'
cpp += block('bool ChatHandler::hasStringAbbr(') + '\n'
cpp += block('ChatCommandSearchResult ChatHandler::FindCommand(') + '\n' + tables
cpp += r'''
int main() {
 ChatHandler gm; gm.security = SEC_ADMINISTRATOR;
 auto check = [](ChatHandler& session, const char* text, bool(ChatHandler::*handler)(char*),const char* args) {
  ChatCommand* command = nullptr;
  assert(session.FindCommand(commands,text,command) == CHAT_COMMAND_OK);
  assert(command && command->Handler == handler);
  assert(std::string(text) == args);
 };
 for (auto prefix : {"t", "te", "tel", "tele", "T", "TELE"}) {
  std::string text = std::string(prefix) + " scarlet monastery";
  check(gm,text.c_str(),&ChatHandler::HandleTeleCommand,"scarlet monastery");
 }
 check(gm,"t name Patch Stormwind",&ChatHandler::HandleTeleNameCommand,"Patch Stormwind");
 check(gm,"tele group Stormwind",&ChatHandler::HandleTeleGroupCommand,"Stormwind");
 check(gm,"tr near",&ChatHandler::HandleTriggerNearCommand,"");
 check(gm,"tp v1 request check sm",&ChatHandler::HandlePlayerTravelCommand,"v1 request check sm");
 ChatHandler player;
 check(player,"tp v1 request check sm",&ChatHandler::HandlePlayerTravelCommand,"v1 request check sm");
 for (const char* text : {"tele Stormwind", "t Stormwind", "tele name Patch Stormwind", "tele add Test"}) {
  ChatCommand* command = nullptr;
  assert(player.FindCommand(commands,text,command) != CHAT_COMMAND_OK);
 }
 std::cout << "Native teleport command routing and rank checks passed\n";
}
'''
with tempfile.TemporaryDirectory(prefix='tele-routing-') as tmp:
    folder = Path(tmp)
    src = folder / 'test.cpp'; src.write_text(cpp)
    exe = folder / 'test.exe'
    args = ['cl', '/nologo', '/EHsc', '/std:c++17', str(src), '/Fe:' + str(exe)] if shutil.which('cl') else ['c++', '-std=c++17', str(src), '-o', str(exe)]
    subprocess.run(args, cwd=folder, check=True)
    subprocess.run([str(exe)], cwd=folder, check=True)
