@echo off
chcp 65001 >nul
title Live2D MCP - Python Setup

set ROOT=%~dp0
set PYTHON_DIR=%ROOT%python
set PYTHON_EXE=%PYTHON_DIR%\python.exe

echo ============================================================
echo   Live2D MCP - Windows Setup
echo ============================================================
echo.

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python not found in %PYTHON_DIR%
    echo Make sure python\python.exe exists.
    echo.
    echo Download "Windows embeddable package" Python 3.12 here:
    echo   https://www.python.org/downloads/windows/
    echo Unpack it into %PYTHON_DIR%
    pause
    exit /b 1
)

echo 0. Enabling site-packages (python312._pth)...
for %%P in ("%PYTHON_DIR%\python*._pth") do (
    findstr /C:"import site" "%%~fP" >nul 2>&1
    if errorlevel 1 (
        echo. >> "%%~fP"
        echo import site >> "%%~fP"
        echo   enabled
    ) else (
        echo   already enabled
    )
)

if not exist "%PYTHON_DIR%\get-pip.py" (
    echo 0b. Downloading get-pip.py...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"
    if errorlevel 1 (
        echo ERROR: could not download get-pip.py. Check internet connection.
        pause
        exit /b 1
    )
)

echo 1. Installing pip...
"%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip installation failed
    pause
    exit /b 1
)
echo.

echo 2. Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: pip upgrade failed, continuing...
)
echo.

echo 3. Installing dependencies...
"%PYTHON_EXE%" -m pip install -r "%ROOT%\requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Some packages may have failed. Check output above.
)

echo.
echo ============================================================
echo   Setup complete!
echo.
echo   Start with: start.bat
echo ============================================================
pause