#!/usr/bin/env python3
"""MCP client for interacting with the Live2D Companion server."""
import os
import sys
import json
import urllib.request
import urllib.error

MCP_URL = "http://127.0.0.1:8765/mcp"
SESSION_FILE = os.path.join(os.path.dirname(__file__), ".mcp_session")

def _get_session():
    try:
        with open(SESSION_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def _save_session(sid):
    with open(SESSION_FILE, "w") as f:
        f.write(sid)

def _rpc(method, params=None, need_session=True):
    sid = _get_session() if need_session else None
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(MCP_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if sid:
        req.add_header("Mcp-Session-Id", sid)
    try:
        resp = urllib.request.urlopen(req)
        if not sid:
            _save_session(resp.headers.get("mcp-session-id", ""))
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "body": e.read().decode()}

def init():
    result = _rpc("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "opencode", "version": "1.0"}
    }, need_session=False)
    return result

def call_tool(name, args=None):
    result = _rpc("tools/call", {"name": name, "arguments": args or {}})
    try:
        return result["result"]["content"][0]["text"]
    except (KeyError, IndexError):
        return json.dumps(result, indent=2, ensure_ascii=False)

def list_tools():
    result = _rpc("tools/list")
    return [t["name"] for t in result.get("result", {}).get("tools", [])]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: mcp_client.py <tool_name> [json_args]")
        sys.exit(1)
    if sys.argv[1] == "init":
        print(init())
        sys.exit(0)
    if sys.argv[1] == "list":
        print("\n".join(list_tools()))
        sys.exit(0)
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    print(call_tool(tool, args))
