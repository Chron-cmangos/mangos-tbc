#include "Util/Errors.h"
#include <windows.h>
#include <cstdlib>
#include <exception>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
    MaNGOS::InstallFatalHandlers();
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    if (argc != 2) return 2;
    std::string const mode = argv[1];
    if (mode == "assert") MANGOS_ASSERT(false);
    if (mode == "terminate") std::terminate();
    if (mode == "exception") throw std::runtime_error("fatal probe exception");
    if (mode == "abort") std::abort();
    if (mode == "seh") RaiseException(EXCEPTION_ACCESS_VIOLATION, EXCEPTION_NONCONTINUABLE, 0, nullptr);
    int evaluated = 0;
    MANGOS_ASSERT(++evaluated == 1);
    // Existing core and playerbot calls also omit the trailing semicolon.
    MANGOS_ASSERT(evaluated == 1)
    MANGOS_ASSERT(evaluated == 1)
    return mode == "normal" && evaluated == 1 ? 0 : 3;
}
