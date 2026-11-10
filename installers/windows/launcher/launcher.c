/*
 * UniConvert Windows launcher.
 *
 * 1. Finds the bundled python\pythonw.exe (preferred) or falls back to a
 *    system pythonw.exe on PATH.
 * 2. Runs <appdir>\main.py, passing every command-line argument verbatim so
 *    Explorer's right-click menu ("Convert with UniConvert..." "%1") works
 *    for any number of selected files.
 * 3. On failure, shows a helpful message box instead of silently dying.
 *
 * Compile (MinGW):
 *   x86_64-w64-mingw32-gcc launcher.c -mwindows -s -O2 -o UniConvert.exe
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <shellapi.h>
#include <stdarg.h>

static int file_exists(const char *path) {
    DWORD a = GetFileAttributesA(path);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

static void errbox(const char *fmt, ...) {
    char buf[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    MessageBoxA(NULL, buf, "UniConvert", MB_ICONERROR | MB_OK | MB_TOPMOST);
}

static int find_python(char *out, size_t cap, const char *appdir) {
    /* 1. bundled python\pythonw.exe */
    _snprintf(out, cap, "%s\\python\\pythonw.exe", appdir);
    if (file_exists(out)) return 1;
    _snprintf(out, cap, "%s\\python\\python.exe", appdir);
    if (file_exists(out)) return 1;
    /* 2. sidecar (unlikely for our layout) */
    _snprintf(out, cap, "%s\\pythonw.exe", appdir);
    if (file_exists(out)) return 1;
    _snprintf(out, cap, "%s\\python.exe", appdir);
    if (file_exists(out)) return 1;
    /* 3. PATH */
    {
        char *p = NULL;
        /* Search PATH for pythonw.exe first */
        if (SearchPathA(NULL, "pythonw.exe", NULL, (DWORD)cap, out, NULL)) return 1;
        if (SearchPathA(NULL, "python.exe",  NULL, (DWORD)cap, out, NULL)) return 1;
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE p, LPSTR c, int s) {
    char appdir[MAX_PATH], exe[MAX_PATH], script[MAX_PATH], cmd[8192];
    int i, nArgs;
    LPWSTR *argvW = CommandLineToArgvW(GetCommandLineW(), &nArgs);

    GetModuleFileNameA(NULL, appdir, MAX_PATH);
    { char *bs = strrchr(appdir, '\\'); if (bs) *bs = 0; }
    _snprintf(script, sizeof(script), "%s\\main.py", appdir);
    if (!file_exists(script)) {
        errbox("Cannot find UniConvert's main.py at:\n%s\n\nThe installation appears broken.", script);
        return 1;
    }
    if (!find_python(exe, sizeof(exe), appdir)) {
        errbox("UniConvert couldn't start.\n\n"
               "No Python runtime was found.\n\n"
               "If you're using a portable install, make sure the python\\ folder "
               "is present next to UniConvert.exe. If you installed via Setup.exe, "
               "please reinstall.");
        return 1;
    }

    /* Build a single command line: "python" "script" [original args...]
     * Use a wide-char buffer so non-ASCII file names work. */
    {
        wchar_t wexe[MAX_PATH], wscript[MAX_PATH], wcmd[16384];
        MultiByteToWideChar(CP_UTF8, 0, exe, -1, wexe, MAX_PATH);
        MultiByteToWideChar(CP_UTF8, 0, script, -1, wscript, MAX_PATH);
        _snwprintf(wcmd, 16384, L"\"%s\" \"%s\"", wexe, wscript);
        /* Append args from index 1 (skip argv[0] which is our own exe path) */
        for (i = 1; i < nArgs; i++) {
            wcsncat(wcmd, L" \"", 16384 - wcslen(wcmd) - 1);
            /* Escape embedded quotes by doubling them, wrap in quotes always */
            wcsncat(wcmd, argvW[i], 16384 - wcslen(wcmd) - 2);
            wcsncat(wcmd, L"\"", 16384 - wcslen(wcmd) - 1);
        }
        LocalFree(argvW);

        wchar_t wappdir[MAX_PATH];
        MultiByteToWideChar(CP_UTF8, 0, appdir, -1, wappdir, MAX_PATH);
        STARTUPINFOW si = {0}; si.cb = sizeof(si);
        PROCESS_INFORMATION pi = {0};
        BOOL ok = CreateProcessW(NULL, wcmd, NULL, NULL, FALSE, 0, NULL,
                                 wappdir, &si, &pi);
        if (!ok) {
            errbox("Could not launch UniConvert.\n\nCommand: %S\n\nError: %lu",
                   wcmd, GetLastError());
            return 1;
        }
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
    }
    return 0;
}
