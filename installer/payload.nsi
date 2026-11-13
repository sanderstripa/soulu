Unicode true
RequestExecutionLevel user
SilentInstall silent
SetCompressor /SOLID lzma
!ifndef BUILD_DIR
!error "BUILD_DIR required"
!endif
!ifndef OUT_FILE
!error "OUT_FILE required"
!endif
Name "Sona Beta 1.0.60"
OutFile "${OUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\Sona"
Icon "${BUILD_DIR}\ui\sona-icon.ico"
UninstallIcon "${BUILD_DIR}\ui\sona-icon.ico"
Section
  nsExec::ExecToStack /TIMEOUT=5000 'taskkill /F /IM Sona.exe'
  Pop $0
  Pop $1
  Sleep 200
  ClearErrors
  SetOutPath "$INSTDIR"
  SetOverwrite on
  File /r "${BUILD_DIR}\*"
  IfErrors install_failed
  ; Earlier previews included build artifacts; remove them during upgrades.
  Delete "$INSTDIR\shared.lib"
  Delete "$INSTDIR\shared.pdb"
  Delete "$INSTDIR\sona.pdb"
  SetOutPath "$INSTDIR\ui"
  File /oname=sona-icon-v20261113.ico "${BUILD_DIR}\ui\sona-icon.ico"
  File /oname=sona-icon-v44.ico "${BUILD_DIR}\ui\sona-icon.ico"
  ; Existing pinned shortcuts may still name v24 or v44. Replace its bytes too rather
  ; than breaking their icon target; newly created shortcuts use the new path.
  File /oname=sona-icon-v24.ico "${BUILD_DIR}\ui\sona-icon.ico"
  Delete "$INSTDIR\ui\sona-icon.jpg"
  ; Typography migration removes the obsolete VPN font on upgrades too.
  Delete "$INSTDIR\ui\vpn\assets\Montserrat.ttf"
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall Sona.exe"
  WriteRegStr HKCU "Software\Sona" "InstallDir" "$INSTDIR"
  CreateDirectory "$SMPROGRAMS\Sona"
  Delete "$SMPROGRAMS\Sona\Sona.lnk"
  Delete "$DESKTOP\Sona.lnk"
  CreateShortcut "$SMPROGRAMS\Sona\Sona.lnk" "$INSTDIR\Sona.exe" "" "$INSTDIR\ui\sona-icon-v20261113.ico" 0 SW_SHOWNORMAL
  CreateShortcut "$DESKTOP\Sona.lnk" "$INSTDIR\Sona.exe" "" "$INSTDIR\ui\sona-icon-v20261113.ico" 0 SW_SHOWNORMAL
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Sona" "DisplayName" "Sona"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Sona" "DisplayIcon" "$INSTDIR\Sona.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Sona" "UninstallString" '$"$INSTDIR\Uninstall Sona.exe$"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Sona" "Publisher" "Sona"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Sona" "DisplayVersion" "1.0.60-beta"
  System::Call 'shell32::SHChangeNotify(i 0x00002000, i 0x0005, w "$INSTDIR\Sona.exe", p 0)'
  System::Call 'shell32::SHChangeNotify(i 0x00002000, i 0x0005, w "$INSTDIR\ui\sona-icon-v24.ico", p 0)'
  System::Call 'shell32::SHChangeNotify(i 0x00002000, i 0x0005, w "$INSTDIR\ui\sona-icon-v20261113.ico", p 0)'
  System::Call 'shell32::SHChangeNotify(i 0x00002000, i 0x0005, w "$INSTDIR\ui\sona-icon-v44.ico", p 0)'
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  IfErrors install_failed
  SetErrorLevel 0
  Goto done
install_failed:
  SetErrorLevel 2
done:
SectionEnd
UninstPage uninstConfirm
UninstPage instfiles
Section "Uninstall"
  DeleteRegValue HKCU "Software\RegisteredApplications" "Sona"
  DeleteRegKey HKCU "Software\Classes\Sona.Url"
  Delete "$DESKTOP\Sona.lnk"
  RMDir /r "$SMPROGRAMS\Sona"
  DeleteRegKey HKCU "Software\Sona"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Sona"
  RMDir /r "$INSTDIR"
SectionEnd
