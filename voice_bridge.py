#!/usr/bin/env python3
"""Voice bridge: avatar mic -> opencode serve -> avatar TTS."""
import sys, json, os, time, urllib.request, subprocess, atexit

MCP_URL = "http://127.0.0.1:8765/mcp"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if sys.platform == "win32":
    OPENCODE_BIN = os.path.join(BASE_DIR, "opencode", "opencode.exe")
else:
    OPENCODE_BIN = os.path.expanduser("~/.opencode/bin/opencode")
SESSION_FILE = os.path.join(BASE_DIR, ".mcp_session")
PORT = 4098
BASE = "http://127.0.0.1:{}".format(PORT)

session_id = None
serve_proc = None

def log(msg):
    print(msg, flush=True)

def rpc(method, params=None):
    global session_id
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(MCP_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if session_id:
        req.add_header("Mcp-Session-Id", session_id)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        if not session_id:
            sid = resp.headers.get("mcp-session-id", "")
            if sid:
                session_id = sid
                with open(SESSION_FILE, "w") as f:
                    f.write(sid)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def init_mcp():
    global session_id
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            session_id = f.read().strip()
    rpc("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "voice-bridge", "version": "1.0"}
    })

def call_mcp(name, args=None):
    r = rpc("tools/call", {"name": name, "arguments": args or {}})
    try:
        return r["result"]["content"][0]["text"]
    except (KeyError, IndexError):
        return json.dumps(r, ensure_ascii=False)

def start_serve():
    global serve_proc
    if sys.platform == "win32":
        subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        subprocess.run(["taskkill", "/F", "/IM", "opencode.exe"], capture_output=True)
    else:
        kill_old = subprocess.run(["lsof", "-ti:{}".format(PORT)], capture_output=True, text=True)
        for pid in kill_old.stdout.strip().split("\n"):
            if pid:
                try: os.kill(int(pid), 9)
                except: pass
    time.sleep(1)
    serve_proc = subprocess.Popen(
        [OPENCODE_BIN, "serve", "--port", str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(30):
        try:
            r = urllib.request.urlopen(BASE + "/global/health", timeout=2)
            if r.status == 200:
                return True
        except: pass
        time.sleep(1)
    return False

def api_post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return {"error": "HTTP {}: {}".format(e.code, body)}
    except Exception as e:
        return {"error": str(e)}

def get_reply_text(data):
    parts = data.get("parts", [])
    texts = []
    for p in parts:
        if p.get("type") == "text":
            texts.append(p.get("text", ""))
        elif p.get("type") == "tool_use":
            for c in p.get("content", []):
                if isinstance(c, dict) and c.get("type") == "text":
                    texts.append(c.get("text", ""))
    if texts:
        return "\n".join(texts)
    return json.dumps(data, ensure_ascii=False)

def cleanup():
    if serve_proc:
        serve_proc.terminate()
        try: serve_proc.wait(timeout=5)
        except: serve_proc.kill()

def main():
    atexit.register(cleanup)

    log("=== Voice Bridge: Mic -> OpenCode -> Avatar ===\n")

    log("[1/4] Connecting to Live2D avatar MCP...")
    init_mcp()
    log("  OK")

    log("\n[2/4] Starting OpenCode server (port {})...".format(PORT))
    if not start_serve():
        log("  FAILED")
        return
    log("  OK")

    log("\n[3/4] Creating session...")
    s = api_post("/session", {"title": "Voice Bridge"})
    if "error" in s:
        log("  FAILED: {}".format(s["error"]))
        return
    oc_session = s["id"]
    log("  Session: {}".format(oc_session))

    log("\n[4/4] Starting microphone...")
    log("  {}".format(call_mcp("start_microphone", {"lang": "ru"})))
    call_mcp("speak", {"text": "Голосовой мост через ОпенКод запущен. Говорите.", "voice": "ru_RU-irina-medium"})

    log("\n--- Voice bridge active. Speak into the microphone. ---\n")

    try:
        while True:
            result = call_mcp("get_microphone_transcript", {"timeout": 10})
            if not result or result in ("{}", "", '""'):
                continue
            try:
                transcript = json.loads(result)
                if isinstance(transcript, dict):
                    transcript = transcript.get("text", "")
            except json.JSONDecodeError:
                transcript = result
            if not transcript or transcript == "":
                continue

            log("You: {}".format(transcript))

            reply_data = api_post("/session/{}/message".format(oc_session), {
                "parts": [{"type": "text", "text": transcript}],
                "model": {"providerID": "ollama-proxy", "modelID": "qwen3:32b"}
            })

            if "error" in reply_data:
                log("Error: {}".format(reply_data["error"]))
                call_mcp("speak", {"text": "Произошла ошибка.", "voice": "ru_RU-irina-medium"})
                continue

            reply = get_reply_text(reply_data)
            log("OpenCode: {}".format(reply[:200]))
            call_mcp("speak", {"text": reply[:500], "voice": "ru_RU-irina-medium"})

    except KeyboardInterrupt:
        log("\nStopping...")
    finally:
        call_mcp("stop_microphone")
        call_mcp("speak", {"text": "Голосовой мост остановлен.", "voice": "ru_RU-irina-medium"})
        cleanup()
        log("Done.")

if __name__ == "__main__":
    main()
