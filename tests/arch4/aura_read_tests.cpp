#include "Memory/SparseListArray.h"
#include <cstdint>
#include <functional>
#include <cmath>
#include <iostream>
#include <cstdlib>
using int32=std::int32_t; using uint32=std::uint32_t; using AuraType=unsigned;
struct Modifier { int32 m_amount=0,m_miscvalue=0; };
struct SpellEntry { int EquippedItemClass=-1; };
struct Aura {
    Modifier modifier; SpellEntry spell;
    Modifier* GetModifier(){return &modifier;}
    SpellEntry const* GetSpellProto() const {return &spell;}
};
struct Item { bool IsFitToSpellRequirements(SpellEntry const*) const {return true;} };
struct Unit {
    using AuraList=std::list<Aura*>;
    ManTech::SparseListArray<Aura*,317> m_modAuras;
    AuraList const& GetAurasByType(AuraType t) const {return m_modAuras.Stable(t);}
    bool HasAuraType(AuraType t) const {return !m_modAuras[t].empty();}
#include "aura_read_declarations.inc"
};
#include "aura_read_functions.inc"
#define CHECK(x) do {if(!(x)){std::cerr<<__LINE__<<": " #x<<'\n';std::abort();}}while(false)
int main(){
    using namespace ManTech;
    const auto lists=MemoryLedger::Read(MemoryKind::AuraBuckets).bytes;
    const auto pages=MemoryLedger::Read(MemoryKind::AuraIndexes).bytes;
    {
        Unit u;Item weapon;
        for(unsigned type=0;type<317;++type){
            CHECK(u.GetTotalAuraModifier(type)==0);
            CHECK(u.GetTotalAuraMultiplier(type)==1.f);
            CHECK(u.GetMaxPositiveAuraModifier(type)==0);
            CHECK(u.GetMaxNegativeAuraModifier(type)==0);
            CHECK(u.GetTotalAuraModifierByMiscMask(type,3)==0);
            CHECK(u.GetTotalAuraMultiplierByMiscMask(type,3)==1.f);
            CHECK(u.GetMaxPositiveAuraModifierByMiscMask(type,3)==0);
            CHECK(u.GetMaxNegativeAuraModifierByMiscMask(type,3)==0);
            CHECK(u.GetTotalAuraModifierByMiscValue(type,3)==0);
            CHECK(u.GetTotalAuraMultiplierByMiscValue(type,3)==1.f);
            CHECK(u.GetMaxPositiveAuraModifierByMiscValue(type,3)==0);
            CHECK(u.GetMaxNegativeAuraModifierByMiscValue(type,3)==0);
            CHECK(u.GetMaxPositiveAuraModifierByItemClass(type,&weapon)==0);
        }
        CHECK(MemoryLedger::Read(MemoryKind::AuraBuckets).bytes==lists);
        CHECK(MemoryLedger::Read(MemoryKind::AuraIndexes).bytes==pages);
        Aura positive{{20,1}},negative{{-10,2}},other{{30,1}};
        auto const& stable=u.GetAurasByType(42);auto end=stable.end();
        u.m_modAuras.Mutable(42)={&positive,&negative,&other};
        CHECK(u.GetTotalAuraModifier(42)==40);
        CHECK(std::abs(u.GetTotalAuraMultiplier(42)-1.404f)<.0001f);
        CHECK(u.GetMaxPositiveAuraModifier(42)==30);
        CHECK(u.GetMaxNegativeAuraModifier(42)==-10);
        CHECK(u.GetTotalAuraModifierByMiscMask(42,1)==50);
        CHECK(u.GetTotalAuraModifierByMiscValue(42,2)==-10);
        CHECK(u.GetTotalAuraModifierByMiscMask(42,0)==0);
        CHECK(u.GetTotalAuraMultiplierByMiscMask(42,0)==1.f);
        CHECK(u.GetMaxPositiveAuraModifierByItemClass(42,&weapon)==30);
        CHECK(stable.size()==3&&end==stable.end());
        u.m_modAuras.Mutable(42).clear();
        CHECK(u.GetTotalAuraModifier(42)==0&&end==stable.end());
        u.m_modAuras.Mutable(42).push_back(&positive);
        CHECK(u.GetTotalAuraModifier(42)==20&&stable.front()==&positive);
        // The bot scan's early test keeps populated list behavior and skips all
        // absent types without changing the public stable-reference contract.
        unsigned hits=0;
        for(unsigned type=0;type<317;++type){
            if(!u.HasAuraType(type))continue;
            hits+=static_cast<unsigned>(u.GetAurasByType(type).size());
        }
        CHECK(hits==1);
        CHECK(MemoryLedger::Read(MemoryKind::AuraBuckets).count==1);
        CHECK(MemoryLedger::Read(MemoryKind::AuraIndexes).count==1);
    }
    CHECK(MemoryLedger::Read(MemoryKind::AuraBuckets).bytes==lists);
    CHECK(MemoryLedger::Read(MemoryKind::AuraIndexes).bytes==pages);
    std::cout<<"Production aura calculations: no empty allocation; amounts, masks, mutation and stable-reference lifetime passed\n";
}
