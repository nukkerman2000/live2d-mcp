@echo off
chcp 65001 >nul
title Live2D MCP Server (venv)

set ROOT=%~dp0
if exist "%~dp0python\Scripts\python.exe" (
    set BASE_PYTHON="%~dp0python\Scripts\python.exe"
) else if exist "%~dp0python\python.exe" (
    set BASE_PYTHON="%~dp0python\python.exe"
) else (
    set BASE_PYTHON=python
)

set VENV=%~dp0.venv
set PYTHON="%VENV%\Scripts\python.exe"

echo ============================================================
echo       Live2D MCP Companion - Windows (venv)
echo ============================================================
echo.
echo Using base Python: %BASE_PYTHON%
echo.
if not exist "%PYTHON%" (
    echo Creating virtual environment...
    %BASE_PYTHON% -m venv "%VENV%"
    echo Installing dependencies...
    "%PYTHON%" -m pip install -r "%ROOT%\requirements.txt"
    echo.
)
echo Starting MCP Server + Web UI + TTS...
echo.

%PYTHON% "%ROOT%\run.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Server exited with code %ERRORLEVEL%
    pause
)
