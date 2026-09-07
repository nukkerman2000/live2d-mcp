@echo off
chcp 65001 >nul
title Live2D MCP Server

set ROOT=%~dp0
if exist "%~dp0python\Scripts\python.exe" (
    set PYTHON="%~dp0python\Scripts\python.exe"
) else if exist "%~dp0python\python.exe" (
    set PYTHON="%~dp0python\python.exe"
) else (
    set PYTHON=python
)

echo ============================================================
echo       Live2D MCP Companion - Windows Launcher
echo ============================================================
echo.
echo Starting MCP Server + Web UI + TTS...
echo.

%PYTHON% "%ROOT%\run.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Server exited with code %ERRORLEVEL%
    pause
)
