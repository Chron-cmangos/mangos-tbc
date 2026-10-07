"""Compile actual affected method bodies against a detached-map fixture.

The pinned, unfixed source must fail the fixture; the generated build source
must pass it. This exercises lookup and completion bookkeeping, not a live
teleport or network session.
"""
from pathlib import Path
import subprocess,sys
R=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path(__file__).resolve().parent
era=sys.argv[1]
out=R/'build'/era/'map-lifecycle-regression';out.mkdir(exist_ok=True)
def method(text,signature):
    start=text.index(signature);opening=text.index('{',start);depth=1;i=opening+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]
preamble=r'''
#include <string>
#include <unordered_map>
#include <atomic>
#include <stdexcept>
#include <iostream>
using ObjectGuid = unsigned;
struct Unit {};
struct Map {};
struct Bot {
    bool inWorld=true, teleport=false;
    Map map;
    bool IsInWorld() const {return inWorld;}
    bool IsBeingTeleported() const {return teleport;}
    Map* GetMap() {if (!inWorld) throw std::runtime_error("WorldObject::GetMap(): m_currMap"); return &map;}
};
struct Accessor {
    Unit target;
    Unit* GetUnit(Bot& bot,ObjectGuid) {bot.GetMap(); return &target;}
} sObjectAccessor;
struct PlayerbotAI {Bot* bot; Bot* GetBot() {return bot;} Unit* GetUnit(ObjectGuid);};
enum ActionResult {ACTION_RESULT_IMPOSSIBLE,ACTION_RESULT_FAILED};
struct Action {std::string name="reach spell";};
struct Event {};
struct Engine {
    PlayerbotAI* ai;
    std::unordered_map<std::string,int> actionFailures;
    inline static std::atomic<unsigned> actionFailureCacheEntries{0};
    int targetReads=0;
    std::string GetFailureKey(Action* action,const Event&,ActionResult reason) {
        ++targetReads; ai->GetBot()->GetMap();
        return action->name+std::to_string(reason);
    }
    void ClearActionFailures() {
        actionFailureCacheEntries.fetch_sub((unsigned)actionFailures.size()); actionFailures.clear();
    }
    void ClearFailures(Action*,const Event&);
};
void require(bool result) {if(!result) throw std::runtime_error("regression expectation failed");}
'''
main=r'''
int main() {
 try {
    Bot bot; PlayerbotAI ai{&bot}; Engine engine{&ai}; Action action; Event event;
    engine.actionFailures={{"reach spell0",1},{"reach spell1",1},{"other0",1}};
    Engine::actionFailureCacheEntries=3;
    engine.ClearFailures(&action,event);
    require(engine.actionFailures.size()==1 && Engine::actionFailureCacheEntries==1);
    require(ai.GetUnit(42)==&sObjectAccessor.target);
    // Successful movement has now removed the bot from its old map.
    bot.inWorld=false;
    engine.ClearFailures(&action,event);
    require(engine.actionFailures.empty() && Engine::actionFailureCacheEntries==0);
    require(ai.GetUnit(42)==nullptr);
    // A near teleport may still be marked in-world, but is not targetable yet.
    bot.inWorld=true; bot.teleport=true;
    engine.actionFailures={{"old-map0",1}}; Engine::actionFailureCacheEntries=1;
    engine.ClearFailures(&action,event);
    require(engine.actionFailures.empty() && Engine::actionFailureCacheEntries==0);
    require(ai.GetUnit(42)==nullptr);
    bot.teleport=false;
    int before=engine.targetReads;
    engine.ClearFailures(&action,event);
    require(engine.targetReads==before); // Empty bookkeeping never resolves a target.
    require(ai.GetUnit(0)==nullptr);
    ai.bot=nullptr; require(ai.GetUnit(42)==nullptr);
    std::cout << "Attached lookup, detached completion, near teleport, cache accounting, empty cache and null owner passed\n";
    return 0;
 } catch(const std::exception& ex) {std::cerr<<ex.what()<<'\n'; return 23;}
}
'''
for label,enginepath,aipath in [('unfixed',R/'vendor/playerbots/playerbot/strategy/Engine.cpp',R/'vendor/playerbots/playerbot/PlayerbotAI.cpp'),('fixed',R/'build'/era/'playerbot_lifecycle/Engine.cpp',R/'build'/era/'playerbot_lifecycle/PlayerbotAI.cpp')]:
    engine=enginepath.read_text();ai=aipath.read_text()
    cpp=preamble+method(engine,'void Engine::ClearFailures(')+'\n'+method(ai,'Unit* PlayerbotAI::GetUnit(ObjectGuid guid)')+'\n'+main
    source=out/(label+'.cpp');source.write_text(cpp);exe=out/(label+'.exe')
    subprocess.run(['cl.exe','/nologo','/EHsc','/std:c++17',str(source),'/Fe:'+str(exe),'/Fo:'+str(out/(label+'.obj'))],check=True,cwd=out)
    result=subprocess.run([str(exe)],capture_output=True,text=True)
    expected=23 if label=='unfixed' else 0
    print(label,'exit',result.returncode,result.stdout.strip(),result.stderr.strip())
    assert result.returncode==expected
print(era,'regression reproduced on pinned source and resolved in compiled replacement')
