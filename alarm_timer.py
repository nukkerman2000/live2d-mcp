import os
import json
import time
import random
import logging
import threading
from datetime import datetime

logger = logging.getLogger("AlarmTimer")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

_alarm_active = False
_timer_active = False
_timer_end_time = 0
_alarm_checked_today = ""
_mcp_alarm_checked_today = ""
_mcp_timer_active = False
_mcp_timer_end_time = 0
_trigger_callback = None

DEFAULT_CONFIG = {
    "alarm_enabled": False,
    "alarm_time": "08:00",
    "alarm_text": "Доброе утро! Пора вставать!",
    "alarm_song": "",
    "alarm_repeat": 1,
    "alarm_auto_repeat": False,
    "alarm_mcp_enabled": False,
    "alarm_mcp_text": "",
    "alarm_mcp_time": "",
    "alarm_mcp_song": "",
    "alarm_mcp_repeat": 3,
    "alarm_mcp_auto_repeat": False,
    "alarm_mcp_replay_interval": 3,
    "alarm_mcp_stop_after": 0,
    "alarm_replay_interval": 0,
    "alarm_stop_after": 0,
    "timer_enabled": False,
    "timer_duration": 300,
    "timer_text": "Таймер сработал!",
    "timer_song": "",
    "timer_repeat": 1,
    "timer_auto_repeat": False,
    "timer_mcp_enabled": False,
    "timer_mcp_text": "",
    "timer_mcp_duration": 0,
    "timer_mcp_song": "",
    "timer_mcp_repeat": 3,
    "timer_mcp_auto_repeat": False,
    "timer_mcp_replay_interval": 3,
    "timer_mcp_stop_after": 0,
    "timer_replay_interval": 0,
    "timer_stop_after": 0,
    "music_mcp_enabled": False,
    "hide_mcp_enabled": True,
    "control_mcp_enabled": True,
    "emotion_mcp_enabled": True,
    "screenshot_mcp_enabled": True,
    "random_clicks_enabled": False,
    "rapid_click_threshold": 5,
    "drag_phrase_threshold": 10,
    "rapid_click_window": 2.0,
    "rapid_click_times": [60, 40, 30, 20, 10, 3],
    "climax_enabled": True,
    "climax_duration": 20,
    "climax_block_clicks": True,
    "climax_emotions": ["joy", "surprise", "love", "amusement", "fear", "sad", "anger"],
    "climax_motions": ["Tap", "Flick", "FlickDown", "Tap@Body"],
    "rapid_emotions": ["joy", "surprise", "amusement", "love", "fear", "sad"],
    "rapid_motions": ["Tap", "Flick", "FlickDown", "Tap@Body"],
    "tts_engine": "piper",
    "xtts_speaker": "Claribel Dervla",
}


def _read_cfg():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def _write_cfg(cfg):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            full = json.load(f)
        full.update(cfg)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(full, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Write config: {e}")


def get_settings():
    return _read_cfg()


def save_settings(data):
    cfg = _read_cfg()
    for k in DEFAULT_CONFIG:
        if k in data:
            cfg[k] = data[k]
    _write_cfg(cfg)
    if _trigger_callback:
        _trigger_callback(cfg)


def set_trigger_callback(cb):
    global _trigger_callback
    _trigger_callback = cb


def is_alarm_active():
    return _alarm_active


def is_timer_active():
    return _timer_active


def check_alarm():
    """Called periodically. Returns True if user alarm should fire."""
    global _alarm_checked_today
    cfg = _read_cfg()
    if not cfg.get("alarm_enabled", False):
        return False
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if _alarm_checked_today == today:
        return False
    alarm_t = cfg.get("alarm_time", "08:00")
    current = now.strftime("%H:%M")
    if current == alarm_t:
        _alarm_checked_today = today
        return True
    return False


def check_mcp_alarm():
    """Called periodically. Returns True if MCP alarm should fire."""
    global _mcp_alarm_checked_today
    cfg = _read_cfg()
    if not cfg.get("alarm_mcp_enabled", False):
        return False
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if _mcp_alarm_checked_today == today:
        return False
    alarm_t = cfg.get("alarm_mcp_time", "")
    if not alarm_t:
        return False
    current = now.strftime("%H:%M")
    if current == alarm_t:
        _mcp_alarm_checked_today = today
        return True
    return False


def check_timer():
    """Called periodically. Returns True if user timer expired."""
    global _timer_active, _timer_end_time
    cfg = _read_cfg()
    if cfg.get("timer_enabled", False) and not _timer_active:
        _timer_active = True
        _timer_end_time = time.time() + cfg.get("timer_duration", 300)
        logger.info(f"Timer auto-started for {cfg.get('timer_duration', 300)}s")
    if not _timer_active:
        return False
    if time.time() >= _timer_end_time:
        _timer_active = False
        return True
    return False


def start_timer(seconds=None):
    global _timer_active, _timer_end_time
    cfg = _read_cfg()
    duration = seconds if seconds is not None else cfg.get("timer_duration", 300)
    _timer_active = True
    _timer_end_time = time.time() + duration
    logger.info(f"Timer started for {duration}s")


def stop_timer():
    global _timer_active
    _timer_active = False


def check_mcp_timer():
    """Called periodically. Returns True if MCP timer expired."""
    global _mcp_timer_active, _mcp_timer_end_time
    if not _mcp_timer_active:
        return False
    cfg = _read_cfg()
    if not cfg.get("timer_mcp_enabled", False):
        _mcp_timer_active = False
        return False
    if time.time() >= _mcp_timer_end_time:
        _mcp_timer_active = False
        return True
    return False


def start_mcp_timer(seconds=None):
    global _mcp_timer_active, _mcp_timer_end_time
    cfg = _read_cfg()
    duration = seconds if seconds is not None else cfg.get("timer_mcp_duration", 300)
    _mcp_timer_active = True
    _mcp_timer_end_time = time.time() + duration
    logger.info(f"MCP timer started for {duration}s")


def stop_mcp_timer():
    global _mcp_timer_active
    _mcp_timer_active = False


trigger_event = threading.Event()


def fire_alarm():
    cfg = _read_cfg()
    text = cfg.get("alarm_text", "Будильник!")
    song = cfg.get("alarm_song", "")
    repeat = cfg.get("alarm_repeat", 1)
    auto = cfg.get("alarm_auto_repeat", False)
    replay = cfg.get("alarm_replay_interval", 0)
    stop_after = cfg.get("alarm_stop_after", 0)
    logger.info(f"Alarm fired: {text}")
    return {"type": "alarm", "text": text, "song": song, "repeat": repeat, "auto_repeat": auto, "replay_interval": replay, "stop_after": stop_after}


def fire_mcp_alarm():
    cfg = _read_cfg()
    text = cfg.get("alarm_mcp_text", "Будильник от модели!")
    song = cfg.get("alarm_mcp_song", "")
    repeat = cfg.get("alarm_mcp_repeat", 3)
    auto = cfg.get("alarm_mcp_auto_repeat", False)
    replay = cfg.get("alarm_mcp_replay_interval", 3)
    stop_after = cfg.get("alarm_mcp_stop_after", 0)
    logger.info(f"MCP alarm fired: {text}")
    return {"type": "alarm", "text": text, "song": song, "repeat": repeat, "auto_repeat": auto, "replay_interval": replay, "stop_after": stop_after}


def fire_timer():
    cfg = _read_cfg()
    text = cfg.get("timer_text", "Таймер!")
    song = cfg.get("timer_song", "")
    repeat = cfg.get("timer_repeat", 1)
    auto = cfg.get("timer_auto_repeat", False)
    replay = cfg.get("timer_replay_interval", 0)
    stop_after = cfg.get("timer_stop_after", 0)
    logger.info(f"Timer fired: {text}")
    return {"type": "timer", "text": text, "song": song, "repeat": repeat, "auto_repeat": auto, "replay_interval": replay, "stop_after": stop_after}


def fire_mcp_timer():
    cfg = _read_cfg()
    text = cfg.get("timer_mcp_text", "Таймер от модели!")
    song = cfg.get("timer_mcp_song", "")
    repeat = cfg.get("timer_mcp_repeat", 3)
    auto = cfg.get("timer_mcp_auto_repeat", False)
    replay = cfg.get("timer_mcp_replay_interval", 3)
    stop_after = cfg.get("timer_mcp_stop_after", 0)
    logger.info(f"MCP timer fired: {text}")
    return {"type": "timer", "text": text, "song": song, "repeat": repeat, "auto_repeat": auto, "replay_interval": replay, "stop_after": stop_after}
