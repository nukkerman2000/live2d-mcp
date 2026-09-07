@echo off
chcp 65001 >nul
title Live2D MCP Server

:: Try portable python first, then system python
set ROOT=%~dp0
if exist "%~dp0python\Scripts\python.exe" (
    set PYTHON=%~dp0python\Scripts\python.exe
) else if exist "%~dp0python\python.exe" (
    set PYTHON=%~dp0python\python.exe
) else (
    set PYTHON=python
)

echo ============================================================
echo       Live2D MCP Companion - Windows Launcher
echo ============================================================
echo.
echo Python: %PYTHON%
echo.
echo Starting services...
echo   - MCP Server on http://127.0.0.1:8765/mcp
echo   - Web UI    on http://127.0.0.1:8766
echo.
echo Close window to stop.
echo.

"%PYTHON%" "%ROOT%\run.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Server exited with code %ERRORLEVEL%
    pause
)
