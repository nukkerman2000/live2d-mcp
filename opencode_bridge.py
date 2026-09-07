#!/usr/bin/env python3
"""OpenCode bridge: route recognized speech to OpenCode (opencode serve) and speak the reply."""
import os
import sys
import json
import time
import threading
import urllib.request
import subprocess
import logging

logger = logging.getLogger("OCBridge")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CANDIDATE_BINS = [
    os.path.join(BASE_DIR, "opencode", "opencode.exe"),
    os.path.join(BASE_DIR, "opencode", "opencode"),
    os.path.expanduser("~/.opencode/bin/opencode"),
    os.path.expanduser(r"~\AppData\Roaming\npm\opencode.cmd"),
    "opencode",
]


def _find_bin():
    for p in CANDIDATE_BINS:
        if p == "opencode":
            try:
                r = subprocess.run(["opencode", "--version"], capture_output=True, timeout=10)
                if r.returncode == 0:
                    return p
            except Exception:
                continue
            continue
        if not os.path.exists(p):
            continue
        try:
            r = subprocess.run([p, "--version"], capture_output=True, timeout=10)
            if r.returncode == 0:
                return p
        except Exception:
            continue
    return None


PORT = 4101
BASE = "http://127.0.0.1:{}".format(PORT)

DEFAULT_MODEL = {"providerID": "opencode", "modelID": "deepseek-v4-flash-free"}

_state_lock = threading.Lock()
_serve_proc = None
_session_id = None
_enabled = False
_last_text = ""


def is_enabled():
    with _state_lock:
        return _enabled


def set_enabled(v):
    global _enabled
    with _state_lock:
        _enabled = bool(v)


def _api_post(path, body, timeout=120):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": "HTTP {}: {}".format(e.code, e.read().decode()[:300])}
    except Exception as e:
        return {"error": str(e)}


def _ensure_serve():
    global _serve_proc
    # Reuse an already-running opencode serve on our port if healthy
    try:
        r = urllib.request.urlopen(BASE + "/global/health", timeout=2)
        if r.status == 200:
            return True
    except Exception:
        pass
    with _state_lock:
        if _serve_proc is not None and _serve_proc.poll() is None:
            return True
        bin_path = _find_bin()
        if not bin_path:
            logger.error("OpenCode binary not found")
            return False
        env = dict(os.environ)
        env.pop("OPENCODE_SERVER_PASSWORD", None)
        env.pop("OPENCODE_SERVER_USERNAME", None)
        _serve_proc = subprocess.Popen(
            [bin_path, "serve", "--port", str(PORT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=env
        )
    for _ in range(30):
        try:
            r = urllib.request.urlopen(BASE + "/global/health", timeout=2)
            if r.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _ensure_session():
    global _session_id
    with _state_lock:
        sid = _session_id
    if sid:
        return sid
    if not _ensure_serve():
        return None
    s = _api_post("/session", {"title": "Voice"})
    if "error" in s:
        logger.error("Session error: %s", s["error"])
        return None
    with _state_lock:
        _session_id = s.get("id")
        sid = _session_id
    logger.info("Session: %s", sid)
    return sid


def send_and_reply(text, model=None):
    """Send text to OpenCode session, return reply text (or None on failure)."""
    sid = _ensure_session()
    if not sid:
        return None
    body = {"parts": [{"type": "text", "text": text}]}
    if model:
        body["model"] = model
    else:
        body["model"] = DEFAULT_MODEL
    data = _api_post("/session/{}/message".format(sid), body)
    if "error" in data:
        logger.error("Message error: %s", data["error"])
        return None
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
    return None


def stop():
    global _serve_proc, _session_id, _enabled
    with _state_lock:
        _enabled = False
        _session_id = None
        proc = _serve_proc
        _serve_proc = None
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass