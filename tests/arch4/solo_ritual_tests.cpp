#include <cstdlib>
#include <iostream>
#include <algorithm>
#include <cstdint>
using uint32=std::uint32_t;
#define CHECK(x) do { if (!(x)) { std::cerr << __LINE__ << ": " #x " failed\n"; std::abort(); } } while (false)
constexpr int GAMEOBJECT_TYPE_SUMMONING_RITUAL=18, TYPEID_PLAYER=4, CURRENT_CHANNELED_SPELL=1;
constexpr int GO_READY=1;
struct SpellInfo { unsigned Id=43987; };
struct Spell { SpellInfo const* m_spellInfo; };
struct Unit {
    bool alive=true; int type=TYPEID_PLAYER; Spell* channel=nullptr;
    int GetTypeId() const { return type; }
    bool IsAlive() const { return alive; }
    Spell* GetCurrentSpell(int) const { return channel; }
};
struct GameObjectInfo { struct { unsigned reqParticipants=1; } summoningRitual; struct { uint32 delay=0; } summoningRitualCustom; };
struct GameObject {
    bool inWorld=true; int type=GAMEOBJECT_TYPE_SUMMONING_RITUAL;
    unsigned uses=1, spellId=43987; Unit* owner=nullptr; GameObjectInfo info;
    uint32 m_delayedActionTimer=0; int lootState=GO_READY;
    bool IsInWorld() const { return inWorld; }
    int GetGoType() const { return type; }
    auto GetGOInfo() const { return &info; }
    unsigned GetUniqueUseCount() const { return uses; }
    unsigned GetSpellId() const { return spellId; }
    Unit* GetOwner() const { return owner; }
    int GetLootState() const { return lootState; }
    bool CanCompleteSoloRitual() const;
    void Schedule();
};
#include "solo_ritual_function.inc"
void GameObject::Schedule() {
#include "solo_ritual_schedule.inc"
}
int main() {
    GameObject go; SpellInfo info; Spell spell{&info}; Unit caster;
    caster.channel=&spell; go.owner=&caster;
    CHECK(go.CanCompleteSoloRitual());
    for (unsigned participants : {0u,2u,3u,5u,10u}) {
        go.info.summoningRitual.reqParticipants=participants;
        CHECK(!go.CanCompleteSoloRitual()); // Multi-user and warlock summons unchanged.
    }
    go.info.summoningRitual.reqParticipants=1;
    go.owner=nullptr; CHECK(!go.CanCompleteSoloRitual()); // Static altars need a click.
    go.owner=&caster; caster.channel=nullptr; CHECK(!go.CanCompleteSoloRitual());
    caster.channel=&spell; info.Id=7720; CHECK(!go.CanCompleteSoloRitual());
    info.Id=43987; caster.alive=false; CHECK(!go.CanCompleteSoloRitual());
    caster.alive=true; caster.type=3; CHECK(!go.CanCompleteSoloRitual());
    caster.type=TYPEID_PLAYER; go.uses=0; CHECK(!go.CanCompleteSoloRitual());
    go.uses=2; CHECK(go.CanCompleteSoloRitual()); // Late helper cannot block completion.
    go.inWorld=false; CHECK(!go.CanCompleteSoloRitual());
    go.inWorld=true; go.type=22; CHECK(!go.CanCompleteSoloRitual());
    go.type=18; go.spellId=0; CHECK(!go.CanCompleteSoloRitual());
    go.spellId=43987; CHECK(go.CanCompleteSoloRitual());
    go.Schedule(); CHECK(go.m_delayedActionTimer==1); // Defer zero-delay completion.
    go.info.summoningRitualCustom.delay=5000;
    go.Schedule(); CHECK(go.m_delayedActionTimer==1); // Never reset an active timer.
    go.m_delayedActionTimer=0; go.Schedule(); CHECK(go.m_delayedActionTimer==5000);
    go.m_delayedActionTimer=0; go.lootState=3; go.Schedule(); CHECK(go.m_delayedActionTimer==0);
    go.lootState=GO_READY;
    caster.channel=nullptr; CHECK(!go.CanCompleteSoloRitual()); // No repeat after completion.
    go.Schedule(); CHECK(go.m_delayedActionTimer==0);
    std::cout << "Production solo ritual eligibility: creator, static, multi-user, cancellation, death, wrong channel and repeat cases passed\n";
}
