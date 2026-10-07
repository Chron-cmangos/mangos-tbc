#ifndef MANTECH_ENTITY_LEDGER_H
#define MANTECH_ENTITY_LEDGER_H
#include <array>
#include <atomic>
#include <cstdint>
namespace ManTech
{
enum class EntityKind : unsigned { Players, Creatures, Pets, Items, GameObjects, Corpses, DynamicObjects, AuraEffects, AuraHolders, Count };
class EntityLedger
{
    inline static std::array<std::atomic<std::uint64_t>, static_cast<unsigned>(EntityKind::Count)> counts{};
public:
    static void Add(EntityKind kind) { counts[static_cast<unsigned>(kind)].fetch_add(1, std::memory_order_relaxed); }
    static void Remove(EntityKind kind) { counts[static_cast<unsigned>(kind)].fetch_sub(1, std::memory_order_relaxed); }
    static std::uint64_t Read(EntityKind kind) { return counts[static_cast<unsigned>(kind)].load(std::memory_order_relaxed); }
    static const char* Name(EntityKind kind)
    {
        constexpr const char* names[] = {"players", "creatures_including_pets", "pets", "items_including_bags", "gameobjects", "corpses", "dynamicobjects", "aura_effects", "aura_holders"};
        return names[static_cast<unsigned>(kind)];
    }
};
}
#endif
