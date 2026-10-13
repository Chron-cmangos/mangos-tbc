#include "Util/FatalError.h"
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <csignal>
#include <atomic>

#ifdef _WIN32
#include <windows.h>
#ifdef _MSC_VER
#include <intrin.h>
#endif
#endif

namespace
{
    std::atomic<void (*)(char const*, void*)> fatalReporter{nullptr};
    [[noreturn]] void ReportFatalError(char const* reason, void* caller)
    {
#ifdef _WIN32
        // Preserve a small receipt before the full symbol/dump machinery. Use
        // Win32 I/O rather than the world logger or its locks during failure.
        char module[MAX_PATH] = {}, path[MAX_PATH] = {}, receipt[4096] = {};
        DWORD const length = GetModuleFileNameA(nullptr, module, MAX_PATH);
        if (length && length < MAX_PATH)
        {
            char* end = module + length;
            while (end != module && end[-1] != '\\') --end;
            *end = '\0';
            if (_snprintf_s(path, sizeof(path), _TRUNCATE, "%sCrashes", module) > 0)
            {
                CreateDirectoryA(path, nullptr);
                int const result = _snprintf_s(path, sizeof(path), _TRUNCATE,
                    "%sCrashes\\FatalError-%lu-%lu-%llu.txt", module,
                    GetCurrentProcessId(), GetCurrentThreadId(), GetTickCount64());
                if (result >= 0)
                {
                    HANDLE file = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                        CREATE_NEW, FILE_FLAG_WRITE_THROUGH, nullptr);
                    if (file != INVALID_HANDLE_VALUE)
                    {
                        SYSTEMTIME now;
                        GetSystemTime(&now);
                        int const bytes = _snprintf_s(receipt, sizeof(receipt), _TRUNCATE,
                            "FATAL_EXIT utc=%04u-%02u-%02uT%02u:%02u:%02uZ pid=%lu thread=%lu\r\n%s\r\n",
                            now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond,
                            GetCurrentProcessId(), GetCurrentThreadId(), reason);
                        DWORD written = 0;
                        WriteFile(file, receipt, bytes < 0 ? sizeof(receipt) - 1 : bytes, &written, nullptr);
                        FlushFileBuffers(file);
                        CloseHandle(file);
                    }
                }
            }
        }
        // The existing Windows crash reporter already understands this code
        // and records the message in both its report and the dump comment.
        ULONG_PTR const details[] = {reinterpret_cast<ULONG_PTR>(reason), reinterpret_cast<ULONG_PTR>(caller)};
        // The CRT catches exceptions thrown by a terminate handler. Invoke the
        // installed reporter directly so it cannot swallow the fatal context.
        if (auto reporter = fatalReporter.load(std::memory_order_acquire))
            reporter(reason, caller);
        else
            RaiseException(0xC0000420L, EXCEPTION_NONCONTINUABLE, 2, details);
        // Never continue if an external handler returns or reporting fails.
        TerminateProcess(GetCurrentProcess(), 0xC0000420L);
        ExitProcess(0xC0000420L);
#else
        std::fprintf(stderr, "FATAL_EXIT: %s\n", reason);
        std::fflush(stderr);
        std::abort();
#endif
    }
}

void MaNGOS::SetFatalReporter(void (*reporter)(char const*, void*))
{
    fatalReporter.store(reporter, std::memory_order_release);
}

void MaNGOS::InstallFatalHandlers()
{
#ifdef _WIN32
    // Install after CRT/static initialization, which can replace early handlers.
    std::set_terminate([]() noexcept
    {
        if (std::exception_ptr error = std::current_exception())
        {
            try { std::rethrow_exception(error); }
            catch (std::exception const& ex) { FatalError(ex.what()); }
            catch (...) { FatalError("std::terminate: non-standard exception"); }
        }
        FatalError("std::terminate: no active exception");
    });
    std::signal(SIGABRT, [](int) { FatalError("abort / SIGABRT"); });
#endif
}

[[noreturn]] void MaNGOS::FatalError(char const* reason)
{
#if defined(_WIN32) && defined(_MSC_VER)
    ReportFatalError(reason, _ReturnAddress());
#else
    ReportFatalError(reason, nullptr);
#endif
}

[[noreturn]] void MaNGOS::FatalAssertion(char const* expression, char const* file, unsigned line, char const* function)
{
    char message[2048] = {};
    std::snprintf(message, sizeof(message), "Assertion failed: %s\nFile: %s:%u\nFunction: %s", expression, file, line, function);
#if defined(_WIN32) && defined(_MSC_VER)
    ReportFatalError(message, _ReturnAddress());
#else
    ReportFatalError(message, nullptr);
#endif
}
