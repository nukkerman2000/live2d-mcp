@echo off
chcp 65001 >nul
:: Usage: mcp_call.bat <tool_name> [json_params]

set ROOT=%~dp0

if "%1"=="" (
    echo Usage: mcp_call.bat ^<tool_name^> [json_params]
    echo.
    echo Examples:
    echo   mcp_call.bat get_status
    echo   mcp_call.bat speak "{\"text\":\"Hello\"}"
    exit /b 1
)

set METHOD=%1
set PARAMS=%2
if "%PARAMS%"=="" set PARAMS={}

set SIDFILE=%ROOT%.mcp_session
if not exist "%SIDFILE%" (
    echo Error: No session file found. Start the server first (start.bat)
    exit /b 1
)

set /p SID=<"%SIDFILE%"

if exist "%~dp0python\Scripts\python.exe" (
    set PYTHON=%~dp0python\Scripts\python.exe
) else if exist "%~dp0python\python.exe" (
    set PYTHON=%~dp0python\python.exe
) else (
    set PYTHON=python
)

set TMPFILE=%ROOT%_mcp_call_tmp.py
(
  echo import sys, json, urllib.request as ur
  echo sid = open(r"%SIDFILE%").read().strip()
  echo payload = json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'%METHOD%','arguments':%PARAMS%}}^).encode()
  echo req = ur.Request('http://127.0.0.1:8765/mcp', data=payload, headers={'Content-Type':'application/json','Accept':'application/json','Mcp-Session-Id':sid})
  echo d = json.loads(ur.urlopen(req^).read(^)^)
  echo print(d.get('result',{}).get('content',[{}])[0].get('text',json.dumps(d)^)^)
) > "%TMPFILE%"

%PYTHON% "%TMPFILE%"
set EXITCODE=%ERRORLEVEL%
del "%TMPFILE%"

if %EXITCODE% NEQ 0 (
    echo Error: MCP call failed
    pause
)
