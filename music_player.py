import os
import glob
import threading
import logging
import random as randmod
import time
import json
import sys

logger = logging.getLogger("MusicPlayer")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MP3_DIR = os.path.join(BASE_DIR, "mp3")

if sys.platform == "win32":
    import ctypes
    _winmm = ctypes.windll.winmm

    def _mci(cmd):
        buf = ctypes.create_unicode_buffer(512)
        _winmm.mciSendStringW(cmd, buf, 512, None)
        return buf.value


_playing = False
_current = None
_player_thread = None
_stop_flag = threading.Event()
_stop_requested = False
_loop = False
_autoplay = True
_autoplay_timer = None
_volume = 500
_dance_bpm = 120


def _load_volume():
    global _volume
    try:
        cfg_path = os.path.join(BASE_DIR, "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        vol = cfg.get("music_volume", 0.5)
        _volume = int(max(0, min(1.0, float(vol))) * 1000)
    except Exception:
        pass


_load_volume()


def list_tracks():
    if not os.path.isdir(MP3_DIR):
        return []
    files = sorted(glob.glob(os.path.join(MP3_DIR, "*.mp3")))
    return [os.path.basename(f) for f in files]


def play_track(name: str):
    global _playing, _current, _player_thread, _stop_flag
    stop()
    path = os.path.join(MP3_DIR, name)
    if not os.path.exists(path):
        return f"File not found: {name}"
    _current = name
    _stop_flag.clear()
    _player_thread = threading.Thread(target=_play_loop, args=(path, name), daemon=True)
    _player_thread.start()
    _playing = True
    logger.info(f"Playing: {name}")
    return f"Playing: {name}"


def play_random():
    tracks = list_tracks()
    if not tracks:
        return "No tracks"
    return play_track(randmod.choice(tracks))


def _get_duration(path):
    if sys.platform == "win32":
        _mci(f'open "{path}" type mpegvideo alias _dur')
        dur = _mci("status _dur length") or "0"
        _mci("close _dur")
        try:
            return max(int(dur), 1000) / 1000.0
        except (ValueError, TypeError):
            return 30.0
    else:
        try:
            import mutagen
            a = mutagen.File(path)
            if a is not None and a.info.length:
                return a.info.length
        except Exception:
            pass
        return 30.0


def _play_loop(path, name):
    global _playing, _stop_requested
    try:
        duration = _get_duration(path)
    except Exception:
        duration = 30.0
    try:
        if sys.platform == "win32":
            while not _stop_flag.is_set():
                _mci(f'open "{path}" type mpegvideo alias mcp_music')
                _mci(f"setaudio mcp_music volume to {_volume}")
                _mci("play mcp_music from 0")
                _stop_flag.wait(max(duration - 0.3, 1.0))
                _mci("close mcp_music")
                if _stop_flag.is_set():
                    break
                if not _loop:
                    break
        else:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(_volume / 1000.0)
            while not _stop_flag.is_set():
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and not _stop_flag.is_set():
                    _stop_flag.wait(0.1)
                if _stop_flag.is_set():
                    pygame.mixer.music.stop()
                    break
                if not _loop:
                    break
    except Exception as e:
        logger.error(f"Playback error: {e}")
    finally:
        _playing = False
        if _autoplay and not _loop and not _stop_requested:
            _autoplay_next(name)
        _stop_requested = False


def _autoplay_next(prev_name):
    global _autoplay_timer
    tracks = list_tracks()
    if not tracks or prev_name not in tracks:
        return
    idx = tracks.index(prev_name)
    nxt = tracks[(idx + 1) % len(tracks)]
    _autoplay_timer = threading.Timer(0.3, play_track, args=[nxt])
    _autoplay_timer.start()


def play_next():
    tracks = list_tracks()
    if not tracks:
        return "No tracks"
    global _current
    if _current and _current in tracks:
        idx = tracks.index(_current)
        nxt = tracks[(idx + 1) % len(tracks)]
    else:
        nxt = tracks[0]
    return play_track(nxt)


def play_prev():
    tracks = list_tracks()
    if not tracks:
        return "No tracks"
    global _current
    if _current and _current in tracks:
        idx = tracks.index(_current)
        nxt = tracks[(idx - 1) % len(tracks)]
    else:
        nxt = tracks[-1]
    return play_track(nxt)


def stop():
    global _playing, _stop_requested
    _stop_requested = True
    _stop_flag.set()
    try:
        if sys.platform == "win32":
            _mci("close mcp_music")
        else:
            import pygame
            pygame.mixer.music.stop()
    except Exception:
        pass
    _playing = False
    logger.info("Playback stopped")


def set_volume(vol: int):
    global _volume
    _volume = max(0, min(1000, vol))
    try:
        if sys.platform == "win32":
            _mci(f"setaudio mcp_music volume to {_volume}")
        else:
            import pygame
            pygame.mixer.music.set_volume(_volume / 1000.0)
    except Exception:
        pass


def get_volume() -> int:
    return _volume


def set_loop(v: bool):
    global _loop
    _loop = v


def get_loop() -> bool:
    return _loop


def set_autoplay(v: bool):
    global _autoplay
    _autoplay = v


def get_autoplay() -> bool:
    return _autoplay


def is_playing():
    return _playing


def current_track():
    return _current


def get_dance_rpm() -> float:
    if not _playing:
        return 0.0
    return _dance_bpm / 60.0
