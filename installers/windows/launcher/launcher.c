/*
 * UniConvert Windows launcher.
 * Looks for python3/python next to the launcher, then in PATH,
 * and runs uniconvert\main.py.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

static int file_exists(const char *path) {
    DWORD a = GetFileAttributesA(path);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

static void find_exe(char *out, size_t cap, const char *name) {
    /* 1. App directory\python\python.exe  (bundled) */
    char buf[MAX_PATH];
    GetModuleFileNameA(NULL, buf, MAX_PATH);
    char *bs = strrchr(buf, '\\'); if (bs) *bs = 0;
    _snprintf(out, cap, "%s\\python\\python.exe", buf);
    if (file_exists(out)) return;
    /* 2. App directory\python.exe */
    _snprintf(out, cap, "%s\\python.exe", buf);
    if (file_exists(out)) return;
    /* 3. PATH */
    strncpy(out, name, cap);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE p, LPSTR c, int s) {
    char exe[MAX_PATH], pydir[MAX_PATH], cmd[2048];
    GetModuleFileNameA(NULL, exe, MAX_PATH);
    char *bs = strrchr(exe, '\\'); if (bs) *bs = 0;

    find_exe(pydir, sizeof(pydir), "pythonw.exe");
    if (!file_exists(pydir)) find_exe(pydir, sizeof(pydir), "python.exe");

    _snprintf(cmd, sizeof(cmd),
        "\"%s\" \"%s\\uniconvert\\main.py\" %s",
        pydir, exe, GetCommandLine());

    STARTUPINFOA si = {0}; si.cb = sizeof(si);
    PROCESS_INFORMATION pi = {0};
    BOOL ok = CreateProcessA(NULL, cmd, NULL, NULL, FALSE, 0, NULL, exe, &si, &pi);
    if (!ok) {
        /* Fall back to a helpful message box. */
        char msg[1024];
        _snprintf(msg, sizeof(msg),
            "UniConvert requires Python 3.9+ and PyQt6/Pillow.\n\n"
            "We tried to run:\n%s\n\n"
            "Please install Python 3 from https://python.org, then run:\n"
            "  pip install PyQt6 Pillow pandas openpyxl PyYAML\n\n"
            "Error: CreateProcess failed (%lu).", cmd, GetLastError());
        MessageBoxA(NULL, msg, "UniConvert", MB_ICONERROR | MB_OK);
        return 1;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
