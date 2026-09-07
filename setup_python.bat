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
    pause
    exit /b 1
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
"%PYTHON_DIR%\Scripts\python.exe" -m pip install --upgrade pip
echo.

echo 3. Installing dependencies...
"%PYTHON_DIR%\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt"
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
