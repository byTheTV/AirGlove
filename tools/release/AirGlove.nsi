Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!include "WinVer.nsh"

!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\AirGlove"
Name "AirGlove"
OutFile "${OutputFile}"
InstallDir "$LOCALAPPDATA\Programs\AirGlove"
InstallDirRegKey HKCU "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
Icon "${StageDir}\AirGlove.ico"
UninstallIcon "${StageDir}\AirGlove.ico"
VIProductVersion "${AppVersion}.0"
VIAddVersionKey "ProductName" "AirGlove"
VIAddVersionKey "FileDescription" "AirGlove Setup"
VIAddVersionKey "FileVersion" "${AppVersion}"
VIAddVersionKey "ProductVersion" "${AppVersion}"
VIAddVersionKey "LegalCopyright" "AirGlove"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

LangString PlatformError ${LANG_RUSSIAN} "Для AirGlove нужна 64-битная Windows 10 или новее."
LangString PlatformError ${LANG_ENGLISH} "AirGlove requires 64-bit Windows 10 or later."
LangString InUse ${LANG_RUSSIAN} "Закройте AirGlove и повторите установку."
LangString InUse ${LANG_ENGLISH} "Close AirGlove and run setup again."

Function .onInit
  ${IfNot} ${RunningX64}
  ${OrIfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "$(PlatformError)"
    Abort
  ${EndIf}
FunctionEnd

Section "AirGlove"
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  SetOverwrite on
  ClearErrors
  File "${StageDir}\AirGlove.exe"
  IfErrors failed
  File "${StageDir}\Readme.txt"
  File "${StageDir}\THIRD-PARTY-NOTICES.txt"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\AirGlove"
  CreateShortcut "$SMPROGRAMS\AirGlove\AirGlove.lnk" "$INSTDIR\AirGlove.exe"
  CreateShortcut "$SMPROGRAMS\AirGlove\Readme.lnk" "$INSTDIR\Readme.txt"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "AirGlove"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${AppVersion}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\AirGlove.exe,0"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
  Goto done
  failed:
    MessageBox MB_OK|MB_ICONSTOP "$(InUse)" /SD IDOK
    SetErrorLevel 1
    Abort
  done:
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  ClearErrors
  Delete "$INSTDIR\AirGlove.exe"
  IfErrors failed
  Delete "$INSTDIR\Readme.txt"
  Delete "$INSTDIR\THIRD-PARTY-NOTICES.txt"
  Delete "$SMPROGRAMS\AirGlove\AirGlove.lnk"
  Delete "$SMPROGRAMS\AirGlove\Readme.lnk"
  RMDir "$SMPROGRAMS\AirGlove"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Goto done
  failed:
    MessageBox MB_OK|MB_ICONSTOP "$(InUse)" /SD IDOK
    SetErrorLevel 1
    Abort
  done:
SectionEnd
