#include "TrainingdummiesModule.h"

#include "Chat/Chat.h"
#include "Entities/ObjectGuid.h"
#include "Entities/Player.h"

namespace cmangos_module
{
    TrainingdummiesModule::TrainingdummiesModule()
    : Module("TrainingDummies", new TrainingDummiesModuleConfig())
    {
        
    }

    const TrainingDummiesModuleConfig* TrainingdummiesModule::GetConfig() const
    {
        return (TrainingDummiesModuleConfig*)Module::GetConfig();
    }

    void TrainingdummiesModule::OnAddToWorld(Creature* creature)
    {
        if (GetConfig()->enabled)
        {
            if (IsTrainingDummy(creature))
            {
                const uint32 dummyID = creature->GetObjectGuid().GetCounter();
                TrainingDummyStatus& status = trainingDummyStatus[dummyID];
                status.guid = creature->GetObjectGuid();
                status.mapID = creature->GetMapId();
                status.initialized = false;
                status.combatTimer = 0;
            }
        }
    }

    void TrainingdummiesModule::OnDealDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage)
    {
        if (GetConfig()->enabled)
        {
            if (IsTrainingDummy(victim))
            {
                const uint32 dummyID = victim->GetObjectGuid().GetCounter();
                auto it = trainingDummyStatus.find(dummyID);
                if (it != trainingDummyStatus.end())
                {
                    TrainingDummyStatus& status = it->second;
                    status.combatTimer = 10000;
                }
            }
        }
    }

    void TrainingdummiesModule::OnUpdate(uint32 elapsed)
    {
        if (GetConfig()->enabled)
        {
            for (auto& pair : trainingDummyStatus)
            {
                TrainingDummyStatus& status = pair.second;
                if (!status.initialized)
                {
                    Initialize(status);
                }
                else
                {
                    if (status.combatTimer > 0)
                    {
                        status.combatTimer -= elapsed;
                        if (status.combatTimer <= 0)
                        {
                            Creature* dummy = GetDummyCreature(status);
                            if (dummy)
                            {
                                dummy->CombatStop();
                                status.combatTimer = 0;
                            }
                        }
                    }
                }
            }
        }
    }

    Creature* TrainingdummiesModule::GetDummyCreature(const TrainingDummyStatus& status)
    {
        if (!status.guid.IsEmpty())
        {
            Map* map = sMapMgr.FindMap(status.mapID);
            if (map)
            {
                return (Creature*)map->GetUnit(status.guid);
            }
        }

        return nullptr;        
    }

    bool TrainingdummiesModule::IsTrainingDummy(const Unit* creature) const
    {
        if (creature)
        {
            const uint32 entry = creature->GetEntry();
            return entry == TRAINING_DUMMY_NPC_ENTRY1 ||
                   entry == TRAINING_DUMMY_NPC_ENTRY2 ||
                   entry == TRAINING_DUMMY_NPC_ENTRY3;
        }

        return false;
    }

    void TrainingdummiesModule::Initialize(TrainingDummyStatus& status)
    {
        Creature* creature = GetDummyCreature(status);
        if (creature)
        {
            creature->addUnitState(UNIT_STAT_NO_COMBAT_MOVEMENT);
            creature->AI()->SetReactState(REACT_PASSIVE);
            status.initialized = true;
        }
    }
}
