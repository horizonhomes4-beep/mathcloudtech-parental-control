@echo off
setlocal EnableExtensions DisableDelayedExpansion
 title @M Family Safety Guard - Windows Setup
 color 0B
 echo.
 echo  ======================================================================
 echo       @M FAMILY SAFETY GUARD  ^|  SECURE WINDOWS CLIENT INSTALLER
 echo                   (version is shown by the installer below)
 echo  ======================================================================
 echo.
 echo  This installer will:
 echo    - Verify this Windows computer and the device configuration
 echo    - Install or locate a supported 64-bit Python runtime
 echo    - Install the isolated agent and required components
 echo    - Configure protected startup and recovery tasks
 echo    - Verify a live connection to your Firebase project
 echo.
 echo  IMPORTANT: Use a child Windows Standard account, not an Administrator
 echo  account. Device restrictions are not tamper-proof against local admins.
 echo.
 net session >nul 2>&1
 if not "%errorlevel%"=="0" (
   echo  [INFO] Administrator permission is required. Requesting elevation...
   powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
   if errorlevel 1 (echo [ERROR] Could not request administrator permission.& pause & exit /b 1)
   exit /b 0
 )
 where powershell.exe >nul 2>&1
 if errorlevel 1 (echo [ERROR] Windows PowerShell is required.& pause& exit /b 1)
 if not exist "%~dp0install.ps1" (echo [ERROR] install.ps1 is missing. Extract the complete ZIP first.& pause& exit /b 1)
 powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
 set "RC=%ERRORLEVEL%"
 echo.
 if not "%RC%"=="0" (
   color 0C
   echo  ======================================================================
   echo   INSTALLATION FAILED - THIS DEVICE MUST NOT BE CONSIDERED PROTECTED
   echo   Review the diagnostic log path printed above and correct the issue.
   echo  ======================================================================
 ) else (
   color 0A
   echo  ======================================================================
   echo   INSTALLATION AND FIREBASE CONNECTION VERIFICATION SUCCEEDED
   echo   Open the Admin dashboard and confirm that this device is ONLINE.
   echo  ======================================================================
 )
 echo.
 pause
 exit /b %RC%
