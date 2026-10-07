# ManTech's TBC baseline includes the vendored modules. A source branch
# alone does not preserve features if a new CMake cache disables their code.
option(MANTECH_REQUIRE_BASELINE_MODULES "Reject incomplete ManTech world-server module builds" ON)
option(BUILD_MODULES "Build module system" ON)
option(BUILD_MODULE_DUALSPEC "Build dualspec module" ON)
option(BUILD_MODULE_TRAININGDUMMIES "Build trainingdummies module" ON)
option(BUILD_MODULE_TRANSMOG "Build transmog module" ON)
if(MANTECH_REQUIRE_BASELINE_MODULES AND (NOT DEFINED BUILD_GAME_SERVER OR BUILD_GAME_SERVER))
  foreach(feature BUILD_MODULES BUILD_MODULE_DUALSPEC BUILD_MODULE_TRAININGDUMMIES BUILD_MODULE_TRANSMOG)
    if(NOT ${feature})
      message(FATAL_ERROR "Incomplete ManTech baseline: ${feature} must be ON. Reconfigure with -D${feature}=ON. Non-baseline builds require an explicit -DMANTECH_REQUIRE_BASELINE_MODULES=OFF.")
    endif()
  endforeach()
endif()
