; NSIS script to build UniConvert-x.y.z-Setup.exe
; Build with: makensis UniConvert.nsi
!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "UniConvert"
OutFile "UniConvert-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\UniConvert"
RequestExecutionLevel user
Unicode true

!define MUI_ABORTWARNING
!define MUI_ICON "..\..\assets\logo.ico"
!define MUI_UNICON "..\..\assets\logo.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "UniConvert" SecMain
    SetOutPath $INSTDIR
    File /r "..\..\dist\uniconvert\*.*"
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    ; Start-menu shortcut
    CreateDirectory "$SMPROGRAMS\UniConvert"
    CreateShortcut "$SMPROGRAMS\UniConvert\UniConvert.lnk" "$INSTDIR\uniconvert.exe" "" "$INSTDIR\uniconvert.exe" 0
    CreateShortcut "$SMPROGRAMS\UniConvert\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    ; Desktop shortcut
    CreateShortcut "$DESKTOP\UniConvert.lnk" "$INSTDIR\uniconvert.exe" "" "$INSTDIR\uniconvert.exe" 0
    ; Register context-menu entry
    WriteRegStr HKCU "Software\Classes\*\shell\UniConvert" "" "Convert with UniConvert..."
    WriteRegStr HKCU "Software\Classes\*\shell\UniConvert" "Icon" '"$INSTDIR\uniconvert.exe",0'
    WriteRegStr HKCU "Software\Classes\*\shell\UniConvert\command" "" '"$INSTDIR\uniconvert.exe" "%1"'
    WriteRegStr HKCU "Software\Classes\Directory\shell\UniConvert" "" "Convert with UniConvert (folder)..."
    WriteRegStr HKCU "Software\Classes\Directory\shell\UniConvert" "Icon" '"$INSTDIR\uniconvert.exe",0'
    WriteRegStr HKCU "Software\Classes\Directory\shell\UniConvert\command" "" '"$INSTDIR\uniconvert.exe" "%1"'
    ; Add to appwiz (Add/Remove Programs)
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "DisplayName" "UniConvert"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "DisplayIcon" '"$INSTDIR\uniconvert.exe",0'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "DisplayVersion" "0.1.0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert" "Publisher" "UniConvert"
SectionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\UniConvert\UniConvert.lnk"
    Delete "$SMPROGRAMS\UniConvert\Uninstall.lnk"
    RMDir "$SMPROGRAMS\UniConvert"
    Delete "$DESKTOP\UniConvert.lnk"
    DeleteRegKey HKCU "Software\Classes\*\shell\UniConvert"
    DeleteRegKey HKCU "Software\Classes\Directory\shell\UniConvert"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UniConvert"
SectionEnd
