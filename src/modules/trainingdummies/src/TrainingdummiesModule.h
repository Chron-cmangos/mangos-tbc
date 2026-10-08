#ifndef CMANGOS_MODULE_TRAININGDUMMIES_H
#define CMANGOS_MODULE_TRAININGDUMMIES_H

#include "Module.h"
#include "TrainingdummiesModuleConfig.h"

namespace cmangos_module
{
    struct TrainingDummyStatus
    {
        ObjectGuid guid = ObjectGuid();
        bool initialized = false;
        int32 combatTimer = 0;
        uint32 mapID = 0;
    };

    class TrainingdummiesModule : public Module
    {
    public:
        TrainingdummiesModule();
        const TrainingDummiesModuleConfig* GetConfig() const override;

        void OnAddToWorld(Creature* creature) override;
        void OnDealDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage) override;
        void OnUpdate(uint32 elapsed) override;

    private:
        Creature* GetDummyCreature(const TrainingDummyStatus& status);
        bool IsTrainingDummy(const Unit* creature) const;
        void Initialize(TrainingDummyStatus& status);

    private:
        std::unordered_map<uint32, TrainingDummyStatus> trainingDummyStatus;
    };
}
#endif