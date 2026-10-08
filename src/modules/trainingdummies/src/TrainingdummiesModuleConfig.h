#pragma once
#include "ModuleConfig.h"

namespace cmangos_module
{
    #define TRAINING_DUMMY_NPC_ENTRY1 190013
    #define TRAINING_DUMMY_NPC_ENTRY2 190014
    #define TRAINING_DUMMY_NPC_ENTRY3 190015

    class TrainingDummiesModuleConfig : public ModuleConfig
    {
    public:
        TrainingDummiesModuleConfig();
        bool OnLoad() override;

    public:
        bool enabled;
    };
}