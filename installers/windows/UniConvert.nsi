Unicode true
SetCompressor /SOLID lzma
SetCompressorDictSize 64
Name "UniConvert 0.1.1"
OutFile "..\\..\\dist\\release\\UniConvert-0.1.1-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\UniConvert"
InstallDirRegKey HKCU "Software\UniConvert" ""
RequestExecutionLevel user
BrandingText "UniConvert — Universal file converter"
!define MUI_ABORTWARNING
!define MUI_ICON "..\\..\\assets\\logo.ico"
!define MUI_UNICON "..\\..\\assets\\logo.ico"

!include "MUI2.nsh"

; HWND_BROADCAST & WM_SETTINGCHANGE are predefined by modern NSIS

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Core application"
    SetOutPath $INSTDIR
    File /r "..\\..\\dist\\winapp\\*.*"
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Start menu
    CreateDirectory "$SMPROGRAMS\UniConvert"
    CreateShortcut "$SMPROGRAMS\UniConvert\UniConvert.lnk" "$INSTDIR\UniConvert.exe" "" "$INSTDIR\logo.ico" 0
    CreateShortcut "$SMPROGRAMS\UniConvert\Check for updates.lnk" "$INSTDIR\UniConvert.exe" "--update" "$INSTDIR\logo.ico" 0
    CreateShortcut "$SMPROGRAMS\UniConvert\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortcut "$DESKTOP\UniConvert.lnk" "$INSTDIR\UniConvert.exe" "" "$INSTDIR\logo.ico" 0

    ; Right-click context menu for files
    ; Note: HKCR\*\shell entries appear in BOTH the classic context menu and
    ; (on Windows 11) the "Show more options" menu.
    WriteRegStr HKCU "Software\Classes\*\shell\UniConvert" "" "Convert with UniConvert..."
    WriteRegStr HKCU "Software\Classes\*\shell\UniConvert" "Icon" '"$INSTDIR\UniConvert.exe",0'
    WriteRegStr HKCU "Software\Classes\*\shell\UniConvert" "MultiSelectModel" "Player"
    WriteRegStr HKCU "Software\Classes\*\shell\UniConvert\command" "" '"$INSTDIR\UniConvert.exe" "%1"'

    ; Right-click for folders
    WriteRegStr HKCU "Software\Classes\Directory\shell\UniConvert" "" "Convert with UniConvert (folder)..."
    WriteRegStr HKCU "Software\Classes\Directory\shell\UniConvert" "Icon" '"$INSTDIR\UniConvert.exe",0'
    WriteRegStr HKCU "Software\Classes\Directory\shell\UniConvert\command" "" '"$INSTDIR\UniConvert.exe" "%1"'

    ; Right-click for folder background (empty area)
    WriteRegStr HKCU "Software\Classes\Directory\Background\shell\UniConvert" "" "Convert with UniConvert..."
    WriteRegStr HKCU "Software\Classes\Directory\Background\shell\UniConvert" "Icon" '"$INSTDIR\UniConvert.exe",0'
    WriteRegStr HKCU "Software\Classes\Directory\Background\shell\UniConvert\command" "" '"$INSTDIR\UniConvert.exe" "%V"'

    ; Also register for ALL files (HKCR\AllFilesystemObjects) for Win11 visibility
    WriteRegStr HKCU "Software\Classes\AllFilesystemObjects\shell\UniConvert" "" "Convert with UniConvert..."
    WriteRegStr HKCU "Software\Classes\AllFilesystemObjects\shell\UniConvert" "Icon" '"$INSTDIR\UniConvert.exe",0'
    WriteRegStr HKCU "Software\Classes\AllFilesystemObjects\shell\UniConvert\command" "" '"$INSTDIR\UniConvert.exe" "%1"'

    ; Add/Remove Programs
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "DisplayName" "UniConvert"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "DisplayIcon" '"$INSTDIR\UniConvert.exe",0'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "DisplayVersion" "0.1.1"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "Publisher" "UniConvert"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "URLInfoAbout" "https://github.com/Comet-Suite/UniConvert"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "NoRepair" 1
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "EstimatedSize" "110000"

    WriteRegStr HKCU "Software\UniConvert" "" "$INSTDIR"

    ; Notify the shell that file associations have changed so the context-menu
    ; shows up without requiring a logoff/reboot.
    SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment"
SectionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\UniConvert\UniConvert.lnk"
    Delete "$SMPROGRAMS\UniConvert\Check for updates.lnk"
    Delete "$SMPROGRAMS\UniConvert\Uninstall.lnk"
    RMDir "$SMPROGRAMS\UniConvert"
    Delete "$DESKTOP\UniConvert.lnk"
    DeleteRegKey HKCU "Software\Classes\*\shell\UniConvert"
    DeleteRegKey HKCU "Software\Classes\Directory\shell\UniConvert"
    DeleteRegKey HKCU "Software\Classes\Directory\Background\shell\UniConvert"
    DeleteRegKey HKCU "Software\Classes\AllFilesystemObjects\shell\UniConvert"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert"
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "UniConvert"
    DeleteRegKey HKCU "Software\UniConvert"
    SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment"
SectionEnd
