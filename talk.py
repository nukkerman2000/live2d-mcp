import sys, os, json, urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

BASE = "http://127.0.0.1:8765/mcp"
HDR = {"Content-Type": "application/json", "Accept": "application/json"}

def _req(url, payload, sid=None, timeout=15):
    h = dict(HDR)
    if sid: h["mcp-session-id"] = sid
    d = json.dumps(payload).encode()
    r = urllib.request.Request(url, data=d, headers=h)
    return urllib.request.urlopen(r, timeout=timeout)

sid = None
def ensure_session():
    global sid
    if sid: return sid
    resp = _req(BASE, {"jsonrpc":"2.0","id":"init","method":"initialize",
        "params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"talk","version":"1.0"}}})
    sid = resp.headers.get("mcp-session-id")
    _req(BASE, {"jsonrpc":"2.0","method":"notifications/initialized"}, sid)
    return sid

def call(method, params=None):
    s = ensure_session()
    r = _req(BASE, {"jsonrpc":"2.0","id":1,"method":"tools/call",
        "params":{"name":method,"arguments":params or {}}}, s, timeout=30)
    return json.loads(r.read().decode())

EMO_PARAMS = {
    "joy":       {"ParamMouthForm": 0.8},
    "surprise":  {"ParamMouthOpenY": 0.5, "ParamBrowLForm": 1.0, "ParamBrowRForm": 1.0},
    "anger":     {"ParamBrowLForm": -1.0, "ParamBrowRForm": -1.0, "ParamMouthForm": -0.5},
    "sadness":   {"ParamBrowLForm": 0.3, "ParamBrowRForm": 0.3, "ParamMouthForm": -0.5},
    "love":      {"ParamMouthForm": 0.6},
    "amusement": {"ParamMouthForm": 1.0, "ParamMouthOpenY": 0.3},
    "neutral":   {},
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python talk.py <emotion> <text...>")
        sys.exit(1)
    emotion = sys.argv[1]
    text = " ".join(sys.argv[2:])
    ensure_session()
    if emotion:
        call("set_emotion", {"emotion": emotion})
    for name, val in EMO_PARAMS.get(emotion, {}).items():
        call("set_parameter", {"name": name, "value": val})
    r = call("speak", {"text": text})
    c = r.get("result", {}).get("content", [{}])
    print(c[0].get("text", ""))
