"""Compile actual visibility-cleanup bodies against controlled world interfaces.

No realm, database, or production process is started. --baseline demonstrates
the old behavior using the source of the deployed Arch 3 revision.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path
from movement_height_regression import block


HARNESS = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <deque>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>
#define DEBUG_FILTER_LOG(...) ((void)0)
constexpr int TYPEID_UNIT=1, TYPEID_PLAYER=2, TYPEMASK_UNIT=1;
struct ObjectGuid {
    int id=0;
    ObjectGuid()=default;
    ObjectGuid(int n):id(n){}
    bool operator<(ObjectGuid o) const { return id<o.id; }
    bool operator==(ObjectGuid o) const { return id==o.id; }
    bool IsMOTransport() const { return id==900001; }
};
using GuidSet=std::set<ObjectGuid>;
struct Player; struct Map; struct WorldObject; struct Creature; struct Unit;
using WorldObjectSet=std::set<WorldObject*>;
struct Session { int sends=0; };
struct WorldPacket {};
struct UpdateData {
    GuidSet removed;
    void AddOutOfRangeGUID(GuidSet const& ids) { removed.insert(ids.begin(),ids.end()); }
    bool HasData() const { return !removed.empty(); }
    void SendData(Session& s) { ++s.sends; }
    void AddAfterCreatePacket(WorldPacket const&) {}
};
struct Visibility {
    bool overridden=false;
    bool IsVisibilityOverridden() const { return overridden; }
};
struct WorldObject {
    ObjectGuid guid; int type=TYPEID_UNIT; bool visible=true;
    Visibility visibility;
    std::set<Player*> clients;
    ObjectGuid GetObjectGuid() const { return guid; }
    int GetTypeId() const { return type; }
    bool IsPlayer() const { return type==TYPEID_PLAYER; }
    bool isType(int) const { return true; }
    Visibility& GetVisibilityData() { return visibility; }
};
struct Unit:WorldObject {};
struct Creature:Unit {};
struct GenericTransport { std::vector<WorldObject*> passengers;
    auto const& GetPassengers() const { return passengers; }
};
struct Map {
    std::map<ObjectGuid,WorldObject*> objects;
    std::set<ObjectGuid> m_objRemoveList;
    std::deque<ObjectGuid> m_objRemoveOrder;
    int infiniteCalls=0;
    WorldObject* GetWorldObject(ObjectGuid id) {
        auto it=objects.find(id); return it==objects.end()?nullptr:it->second;
    }
    void UpdateInfinite(Player&,UpdateData&,GuidSet& ids,WorldObjectSet&) {
        ++infiniteCalls; ids.erase(ObjectGuid(900002));
    }
    void RememberRemovedObject(ObjectGuid);
};
struct Player:Unit {
    bool real=true, phase=false;
    Map* map=nullptr; GenericTransport* transport=nullptr;
    GuidSet guids; Session session;
    int beforeDestroy=0;
    Player() { type=TYPEID_PLAYER; }
    bool isRealPlayer() const { return real; }
    Map* GetMap() { return map; }
    Session* GetSession() { return &session; }
    GuidSet& GetClientGuids() { return guids; }
    GenericTransport* GetTransport() { return transport; }
    void AddAtClient(WorldObject* obj) { guids.insert(obj->guid); obj->clients.insert(this); }
    void RemoveAtClient(WorldObject* obj) { guids.erase(obj->guid); obj->clients.erase(this); }
    bool IsPendingPhaseChange() const { return phase; }
    void RemovePendingPhaseChange() { phase=false; }
    void BeforeVisibilityDestroy(Creature*) { ++beforeDestroy; }
    void UpdateVisibilityOf(Player*,WorldObject* obj,UpdateData&) {
        if (!obj->visible) RemoveAtClient(obj);
    }
    void UpdateVisibilityOf(Player* p,WorldObject* obj,UpdateData& d,WorldObjectSet&) {
        UpdateVisibilityOf(p,obj,d);
    }
    void SendAuraDurationsForTarget(Unit*) {}
    static std::vector<WorldPacket> BuildAurasForTarget(Player&,Unit const&) { return {}; }
};
struct Camera { Player* owner; Player* GetOwner() { return owner; } };
struct Logger { int count=0; template<class... T> void outCustomLog(T...) { ++count; } } sLog;
struct VisibleNotifier {
    Camera& i_camera; GuidSet i_clientGUIDs; UpdateData& i_data;
    WorldObjectSet i_visibleNow; bool i_processSend;
    VisibleNotifier(Camera& c,UpdateData& d,bool send):i_camera(c),i_clientGUIDs(c.owner->guids),i_data(d),i_processSend(send){}
    void Notify();
};
__NOTIFY__
__HISTORY__
void require(bool ok,char const* msg) { if(!ok) { std::cerr << "FAIL: " << msg << '\n'; std::exit(1); } }
void roaming(bool real) {
    Map map; Player p; p.map=&map; p.real=real; Camera c{&p};
    std::vector<Creature> objects(6400);
    for(int tick=0;tick<200;++tick) {
        UpdateData data; VisibleNotifier notify(c,data,true);
        for(int j=0;j<32;++j) {
            int n=tick*32+j; objects[n].guid=ObjectGuid(n+1);
            map.objects[objects[n].guid]=&objects[n];
            p.AddAtClient(&objects[n]);
            notify.i_clientGUIDs.erase(objects[n].guid);
        }
        notify.Notify();
        require(p.guids.size()==32,"roaming retains only current visible GUIDs, not every visited cell");
        if(tick) require(objects[(tick-1)*32].clients.empty(),"reverse visibility index cleaned");
    }
#ifdef ENABLE_PLAYERBOTS
    if(!real) require(p.session.sends==0,"bot-only cleanup does not enable final client notifications");
#endif
    if(real) require(p.session.sends>0,"human out-of-range packets still sent");
}
void missing(bool real) {
    Map map; Player p; p.map=&map; p.real=real; p.guids.insert(ObjectGuid(55));
    sLog.count=0;
    Camera c{&p}; UpdateData data; VisibleNotifier(c,data,true).Notify();
    require(p.guids.empty(),"missing world object does not leave a dangling client GUID");
#ifdef ENABLE_PLAYERBOTS
    require(sLog.count==(real?1:0),"bot orphan cleanup adds no synchronous diagnostic log");
#else
    require(sLog.count==1,"human diagnostic preserved without playerbots");
#endif
}
void exceptions(bool real) {
    Map map; Player p; p.map=&map; p.real=real; Camera c{&p};
    Creature passenger,farVisible,farHidden,ship,infinite;
    passenger.guid=1; farVisible.guid=2; farHidden.guid=3; ship.guid=900001; infinite.guid=900002;
    farVisible.visibility.overridden=true; farHidden.visibility.overridden=true; farHidden.visible=false;
    for(auto* obj:{&passenger,&farVisible,&farHidden,&ship,&infinite}) {
        map.objects[obj->guid]=obj; p.AddAtClient(obj);
    }
    GenericTransport transport; transport.passengers.push_back(&passenger);
    p.transport=&transport; p.phase=true;
    UpdateData data; VisibleNotifier(c,data,false).Notify();
    require(p.guids.count(passenger.guid)==1,"transport passenger remains visible");
    require(p.guids.count(ship.guid)==1,"moving transport retains its special visibility");
    require(p.guids.count(farVisible.guid)==1,"overridden visibility remains visible");
    require(p.guids.count(farHidden.guid)==0,"overridden but invisible object is removed");
    require(p.guids.count(infinite.guid)==1 && map.infiniteCalls==1 && !p.phase,"phase-change infinite visibility handling preserved");
}
int main() {
    for(bool real:{false,true}) { roaming(real); missing(real); exceptions(real); }
    Map history;
    for(int n=1;n<=100000;++n) history.RememberRemovedObject(ObjectGuid(n));
    require(history.m_objRemoveList.size()==4096 && history.m_objRemoveOrder.size()==4096,"removed-object diagnostic history is bounded");
    require(!history.m_objRemoveList.count(ObjectGuid(1)) && history.m_objRemoveList.count(ObjectGuid(100000)),"history retains latest removals");
    history.RememberRemovedObject(ObjectGuid(100000));
    require(history.m_objRemoveOrder.size()==4096,"duplicate removal does not grow FIFO");
    std::cout << "PASS: roaming, reverse cleanup, missing GUIDs, humans, bots, transports, overridden visibility, phase change, bounded history\n";
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', default='cl')
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    notify_path = 'src/game/Grids/GridNotifiers.cpp'
    if args.baseline:
        notify_src = subprocess.check_output(['git','show','2d929fd901c6b6cbd3b1fc0bc470a586f00b0289:'+notify_path],cwd=root,text=True)
        history = 'void Map::RememberRemovedObject(ObjectGuid guid) { m_objRemoveList.insert(guid); }'
    else:
        notify_src = (root/notify_path).read_text()
        history = block((root/'src/game/Maps/Map.cpp').read_text(),'void Map::RememberRemovedObject(')
    code = HARNESS.replace('__NOTIFY__',block(notify_src,'void VisibleNotifier::Notify()')).replace('__HISTORY__',history)
    with tempfile.TemporaryDirectory(prefix='mantech-visibility-test-') as folder:
        folder=Path(folder)
        source=folder/'visibility.cpp'
        source.write_text(code)
        for bots in (True,False):
            if args.baseline and not bots:
                continue
            exe=folder/('bots.exe' if bots else 'no_bots.exe')
            cmd=[args.compiler,'/nologo','/std:c++20','/EHsc','/Od','/W3','/MD',str(source),'/Fe:'+str(exe),'/Fo:'+str(folder/'test.obj')]
            if bots: cmd.append('/DENABLE_PLAYERBOTS')
            subprocess.run(cmd,cwd=folder,check=True)
            result=subprocess.run([str(exe)],cwd=folder,text=True,capture_output=True,timeout=15)
            print(result.stdout+result.stderr,end='')
            if args.baseline:
                assert result.returncode!=0 and 'roaming retains only current' in result.stderr, 'Expected original roaming-retention failure'
                print('CONFIRMED: deployed baseline fails the roaming-cleanup regression')
            else:
                result.check_returncode()


if __name__=='__main__':
    main()
