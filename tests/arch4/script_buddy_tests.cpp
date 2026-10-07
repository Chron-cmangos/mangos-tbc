#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>
#define CHECK(x) do { if (!(x)) { std::cerr << __LINE__ << ": " #x " failed\n"; std::abort(); } } while (false)
constexpr int TYPEID_PLAYER=4, TYPEID_UNIT=3, DIST_CALC_NONE=0;
constexpr unsigned SCRIPT_FLAG_BUDDY_BY_STRING_ID=2048, SCRIPT_FLAG_ALL_ELIGIBLE_BUDDIES=512;
constexpr unsigned SCRIPT_COMMAND_TERMINATE_SCRIPT=31;
struct WorldObject {
    int type=TYPEID_UNIT; float x=0; bool alive=true;
    int GetTypeId() const { return type; }
    bool IsCreature() const { return type==TYPEID_UNIT; }
    bool IsAlive() const { return alive; }
    float GetDistance(WorldObject* other, bool=true, int=0) const { return std::abs(x-other->x); }
    bool IsWithinDist(WorldObject* other, float range) const { return GetDistance(other)<=range; }
};
using Creature=WorldObject;
struct Map {
    std::vector<WorldObject*>* objects=nullptr;
    auto GetWorldObjects(unsigned) { return objects; }
    unsigned GetId() { return 530; }
};
struct Script {
    unsigned data_flags=SCRIPT_FLAG_BUDDY_BY_STRING_ID, buddyEntry=28011, searchRadiusOrGuid=10, command=31, id=18031;
    bool dead=false;
    bool IsDeadOrDespawnedBuddy() const { return dead; }
};
struct Log { template<class... Args> void outErrorDb(Args...) {} } sLog;
std::pair<bool, bool> resolve(Script* m_script, Map* m_map, WorldObject* originalSource, WorldObject* originalTarget) {
    std::vector<WorldObject*> buddies;
    const char* m_table="dbscripts_on_relay";
    if (false) {}
#include "script_string_buddy.inc"
    return {true, !buddies.empty()};
}
int main() {
    Script script; Map map; WorldObject source;
    auto missing=resolve(&script,&map,&source,nullptr);
    CHECK(missing.first && !missing.second); // Run the termination guard, do not skip it.
    script.command=35;
    CHECK(!resolve(&script,&map,&source,nullptr).first);
    script.command=31;
    std::vector<WorldObject*> objects; map.objects=&objects;
    CHECK(!resolve(&script,&map,&source,nullptr).second);
    WorldObject far{TYPEID_UNIT,100,true}, near{TYPEID_UNIT,3,true}, dead{TYPEID_UNIT,1,false};
    objects={&far,&dead};
    CHECK(!resolve(&script,&map,&source,nullptr).second);
    objects.push_back(&near);
    CHECK(resolve(&script,&map,&source,nullptr).second);
    script.dead=true;
    CHECK(resolve(&script,&map,&source,nullptr).second);
    objects={&near};
    CHECK(!resolve(&script,&map,&source,nullptr).second);
    script.dead=false;
    WorldObject player{TYPEID_PLAYER,1000,true};
    CHECK(resolve(&script,&map,&player,&source).second); // NPC target is the search origin.
    CHECK(!resolve(&script,&map,&player,nullptr).second);
    script.data_flags|=SCRIPT_FLAG_ALL_ELIGIBLE_BUDDIES;
    CHECK(resolve(&script,&map,&source,nullptr).second);
    objects={&far,&dead};
    CHECK(!resolve(&script,&map,&source,nullptr).second);
    std::cout << "Production string-ID selection: absent registry, empty registry, range, liveness, NPC origin and all-buddy cases passed\n";
}
