#pragma once

namespace MaNGOS
{
    void InstallFatalHandlers();
    void SetFatalReporter(void (*reporter)(char const*, void*));
    [[noreturn]] void FatalError(char const* reason);
    [[noreturn]] void FatalAssertion(char const* expression, char const* file, unsigned line, char const* function);
}
