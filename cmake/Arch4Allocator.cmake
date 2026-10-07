option(MANTECH_PROFILE_ALLOCATIONS "Build sampled Windows C++ allocation profiler (diagnostic only)" OFF)
# Pinned, optional allocator for reproducible Arch 4 comparisons.
option(MANTECH_USE_MIMALLOC "Use mimalloc for world-server C++ allocations" OFF)
if(MANTECH_USE_MIMALLOC AND BUILD_GAME_SERVER)
  include(FetchContent)
  set(MI_OVERRIDE OFF CACHE BOOL "Keep CRT malloc/free ownership unchanged" FORCE)
  set(MI_BUILD_STATIC ON CACHE BOOL "" FORCE)
  set(MI_BUILD_SHARED OFF CACHE BOOL "" FORCE)
  set(MI_BUILD_OBJECT OFF CACHE BOOL "" FORCE)
  set(MI_BUILD_TESTS OFF CACHE BOOL "" FORCE)
  FetchContent_Declare(mimalloc
    URL https://codeload.github.com/microsoft/mimalloc/tar.gz/34fbd7e7cd4627424490afe19b20f8066bfc537d
    URL_HASH SHA256=bff20d5423e63d751858dcc4f6ca2d346e16a84f8410f868bc3a298996c1ea1e
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
  FetchContent_MakeAvailable(mimalloc)
  target_compile_definitions(mimalloc-static PRIVATE MI_STAT=1)
endif()
