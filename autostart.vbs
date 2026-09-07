Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\MCP"
WshShell.Run """C:\MCP\python\pythonw.exe"" ""C:\MCP\run.py""", 0, False
