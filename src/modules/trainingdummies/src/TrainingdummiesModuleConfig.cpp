#include "TrainingdummiesModuleConfig.h"

namespace cmangos_module
{
    TrainingDummiesModuleConfig::TrainingDummiesModuleConfig()
    : ModuleConfig("trainingdummies.conf")
    , enabled(false)
    {
    
    }

    bool TrainingDummiesModuleConfig::OnLoad()
    {
        enabled = config.GetBoolDefault("Trainingdummies.Enable", false);
        return true;
    }
}