@echo off
:: Simple installation script for PANFlow on Windows

:: Default installation directory
set INSTALL_DIR=%LOCALAPPDATA%\Programs\PANFlow

:: Parse arguments
set CREATE_SHORTCUT=1

if "%1"=="--no-shortcut" (
    set CREATE_SHORTCUT=0
) else if "%1"=="--help" (
    echo PANFlow installation script
    echo Usage: install.bat [--no-shortcut] [--help]
    echo.
    echo Options:
    echo   --no-shortcut   Don't create a shortcut on the desktop
    echo   --help          Show this help message
    exit /b 0
)

:: Check if the binary exists in the current directory
if not exist panflow-windows.exe (
    echo Binary not found: panflow-windows.exe
    echo Please download the correct binary for Windows first.
    exit /b 1
)

:: Create installation directory
if not exist "%INSTALL_DIR%" (
    echo Creating installation directory: %INSTALL_DIR%
    mkdir "%INSTALL_DIR%"
)

:: Copy binary to installation directory
echo Installing PANFlow to %INSTALL_DIR%...
copy /Y panflow-windows.exe "%INSTALL_DIR%\panflow.exe"

:: Add to PATH (user scope)
echo Adding PANFlow to your PATH...
setx PATH "%PATH%;%INSTALL_DIR%"

:: Create shortcut if requested
if %CREATE_SHORTCUT%==1 (
    echo Creating desktop shortcut...
    :: Using PowerShell to create a shortcut
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('$env:USERPROFILE\Desktop\PANFlow.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\panflow.exe'; $Shortcut.Save()"
)

echo.
echo PANFlow installed successfully!
echo You can now run 'panflow' from the command line.
echo.