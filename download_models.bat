@echo off
chcp 65001 >nul
title Live2D MCP - Download Voice Models

set ROOT=%~dp0

if exist "%~dp0python\python.exe" (
    set PYTHON="%~dp0python\python.exe"
) else (
    set PYTHON=python
)

echo ============================================================
echo   Download Piper voice models + binaries
echo ============================================================
echo.
echo Using: %PYTHON%
echo.

%PYTHON% "%ROOT%\download_models.py" --piper

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: some downloads failed. Check internet connection.
) else (
    echo.
    echo All models downloaded.
)

pause