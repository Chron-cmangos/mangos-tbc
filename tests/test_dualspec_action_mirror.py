"""Compile the actual module save hook and execute its emitted SQL on fixture tables."""
from pathlib import Path
import subprocess
import tempfile
import sqlite3

root = Path(__file__).resolve().parents[1]
def function(text, name):
    start = text.index(name)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

fixture = r'''
#include <map>
#include <string>
#include <vector>
#include <cstdio>
#include <cassert>
#include <iostream>
using uint8=unsigned char; using uint32=unsigned;
enum {ACTIONBUTTON_NEW,ACTIONBUTTON_CHANGED,ACTIONBUTTON_DELETED,ACTIONBUTTON_UNCHANGED};
struct ActionButton {int uState;unsigned action,type;unsigned GetAction(){return action;}unsigned GetType(){return type;}};
using ActionButtonList=std::map<uint8,ActionButton>;
struct Guid {unsigned GetCounter(){return 7;}};
struct Player {bool human=true;bool isRealPlayer(){return human;}Guid GetObjectGuid(){return {};}};
struct Database {std::vector<std::string> sql;template<class...T>void PExecute(const char* format,T...args){
 char buffer[2048];std::snprintf(buffer,sizeof(buffer),format,args...);sql.push_back(buffer);}} CharacterDatabase;
struct Config {bool enabled=true;};
struct DualspecModule {Config config;Config* GetConfig(){return &config;}uint8 GetPlayerActiveSpec(unsigned){return 1;}
 bool OnSaveActionButtons(Player*,ActionButtonList&);};
__METHOD__
int main(){
 Player player;DualspecModule module;ActionButtonList buttons{{1,{ACTIONBUTTON_NEW,100,0}},
 {2,{ACTIONBUTTON_CHANGED,200,0}},{3,{ACTIONBUTTON_DELETED,300,0}},{4,{ACTIONBUTTON_UNCHANGED,400,0}}};
 assert(module.OnSaveActionButtons(&player,buttons));
 assert(buttons.size()==3 && buttons.at(1).uState==ACTIONBUTTON_UNCHANGED && buttons.at(2).uState==ACTIONBUTTON_UNCHANGED);
 assert(CharacterDatabase.sql.size()==5);
 for(const auto& sql:CharacterDatabase.sql)std::cout<<sql<<'\n';
 CharacterDatabase.sql.clear();player.human=false;
 assert(!module.OnSaveActionButtons(&player,buttons) && CharacterDatabase.sql.empty());
 player.human=true;module.config.enabled=false;
 assert(!module.OnSaveActionButtons(&player,buttons) && CharacterDatabase.sql.empty());
 assert(!module.OnSaveActionButtons(nullptr,buttons));
 module.config.enabled=true;buttons.clear();
 assert(module.OnSaveActionButtons(&player,buttons) && CharacterDatabase.sql.size()==2);
}
'''
for realm in (root.name,):
    source = (root/'src/modules/dualspec/src/DualspecModule.cpp').read_text()
    method = function(source, 'bool DualspecModule::OnSaveActionButtons(')
    with tempfile.TemporaryDirectory(prefix='mantech-dualspec-test-') as directory:
        path=Path(directory); cpp=path/'probe.cpp'; exe=path/'probe.exe'
        cpp.write_text(fixture.replace('__METHOD__',method))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_ZERO','/DENABLE_PLAYERBOTS',str(cpp),f'/Fe:{exe}'],cwd=path,check=True,capture_output=True,text=True)
        result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    db=sqlite3.connect(':memory:')
    db.executescript('''CREATE TABLE character_action(guid INT,button INT,action INT,type INT,PRIMARY KEY(guid,button));
      CREATE TABLE custom_dualspec_action(guid INT,button INT,action INT,type INT,spec INT,PRIMARY KEY(guid,button,spec));
      INSERT INTO character_action VALUES(7,1,999,0),(7,9,900,0),(8,9,800,0);
      INSERT INTO custom_dualspec_action VALUES(7,2,999,0,1),(7,3,300,0,1),(7,4,400,0,1),(7,8,800,0,0);''')
    db.executescript(result.stdout)
    assert db.execute('SELECT button,action FROM character_action WHERE guid=7 ORDER BY button').fetchall()==[(1,100),(2,200),(4,400)]
    assert db.execute('SELECT action FROM character_action WHERE guid=8').fetchall()==[(800,)]
    assert db.execute('SELECT action FROM custom_dualspec_action WHERE spec=0').fetchall()==[(800,)]
    print(f'PASS: {realm} actual hook mirrors new/changed/deleted/unchanged active slots, preserves other characters/specs, excludes bots and disabled module')
