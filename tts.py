import os
import sys
import subprocess
import threading
import time
import math
import wave
import json
import logging
import struct
import builtins
import shutil
logger = logging.getLogger("TTS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if sys.platform == "win32":
    PIPER_EXE = os.path.join(BASE_DIR, "piper", "piper.exe")
else:
    PIPER_EXE = shutil.which("piper") or os.path.expanduser("~/.local/bin/piper")
ESPEAK_DATA = os.path.join(BASE_DIR, "piper", "espeak-ng-data")
DEFAULT_VOICE = "ru_RU-irina-medium"

for _d in [os.path.join(BASE_DIR, "voices"), os.path.join(PARENT_DIR, "voices")]:
    if os.path.isdir(_d):
        VOICES_DIR = _d
        break
else:
    VOICES_DIR = os.path.join(BASE_DIR, "voices")
VOICE_CACHE = None

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

_speaking = False
_speech_lock = threading.Lock()
_volume = 1.0
_volume_lock = threading.Lock()
_enabled = True
_enabled_lock = threading.Lock()
_default_voice = DEFAULT_VOICE
_default_voice_lock = threading.Lock()
_speed = 1.0
_speed_lock = threading.Lock()

# XTTS engine state
_xtts = None
_xtts_lock = threading.Lock()
_engine = "piper"  # "piper" or "xtts"
_xtts_speaker = "Claribel Dervla"
_output_device = None  # None = system default

# Piper cached voice instance
_piper_voice_cache: dict[str, tuple] = {}
_piper_voice_cache_lock = threading.Lock()

def _load_settings():
    global _volume, _enabled, _default_voice, _speed, _engine, _xtts_speaker, _output_device
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "default_voice" in cfg:
            _default_voice = cfg["default_voice"]
        if "volume" in cfg:
            _volume = max(0.0, min(1.0, float(cfg["volume"])))
        if "tts_enabled" in cfg:
            _enabled = bool(cfg["tts_enabled"])
        if "tts_speed" in cfg:
            _speed = max(0.25, min(4.0, float(cfg["tts_speed"])))
        if "tts_engine" in cfg:
            _engine = cfg["tts_engine"]
        if "xtts_speaker" in cfg:
            _xtts_speaker = cfg["xtts_speaker"]
        if "output_device" in cfg:
            _output_device = cfg["output_device"]
    except Exception:
        pass
    # Fall back to piper if configured engine is unavailable
    if _engine not in ("piper",) and _engine not in list_engines():
        _engine = "piper"
        if _default_voice.startswith("xtts:"):
            pv = []
            try:
                for f in os.listdir(VOICES_DIR):
                    if f.endswith(".onnx"):
                        pv.append(f[:-5])
            except Exception:
                pass
            if pv:
                _default_voice = pv[0]


def save_settings():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    with _volume_lock:
        cfg["volume"] = _volume
    with _enabled_lock:
        cfg["tts_enabled"] = _enabled
    with _default_voice_lock:
        cfg["default_voice"] = _default_voice
    with _speed_lock:
        cfg["tts_speed"] = _speed
    cfg["tts_engine"] = _engine
    cfg["xtts_speaker"] = _xtts_speaker
    cfg["output_device"] = _output_device
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
    logger.info("Settings saved")


def set_default_voice(v: str):
    voices = list_voices()
    if v not in voices:
        raise ValueError(f"Voice '{v}' not found")
    with _default_voice_lock:
        global _default_voice
        _default_voice = v


def get_default_voice() -> str:
    with _default_voice_lock:
        return _default_voice


def set_speed(s: float):
    with _speed_lock:
        global _speed
        _speed = max(0.25, min(4.0, s))


def get_speed() -> float:
    with _speed_lock:
        return _speed


def set_volume(v: float):
    with _volume_lock:
        global _volume
        _volume = max(0.0, min(1.0, v))


def get_volume() -> float:
    with _volume_lock:
        return _volume


def set_enabled(e: bool):
    with _enabled_lock:
        global _enabled
        _enabled = e


def is_enabled() -> bool:
    with _enabled_lock:
        return _enabled


def get_engine() -> str:
    return _engine


def list_engines() -> list:
    engines = ["piper"]
    try:
        import importlib
        importlib.import_module('TTS.api')
        engines.append("xtts")
    except ImportError:
        pass
    return engines


def set_engine(e: str):
    global _engine
    if e not in list_engines():
        raise ValueError(f"Unknown engine '{e}'")
    _engine = e


def list_voices_by_engine(engine: str = None) -> dict:
    result = {}
    for name, (_, cfg) in _get_voices().items():
        result[name] = os.path.basename(cfg)
        result[f"{name}-child"] = os.path.basename(cfg) + " (child)"
        result[f"{name}-anime"] = os.path.basename(cfg) + " (anime)"
    if engine == "piper":
        return result
    try:
        xtts = _load_xtts()
        for spk in xtts.speakers:
            result[f"xtts:{spk}"] = f"XTTS: {spk}"
    except Exception as e:
        logger.warning(f"Cannot list XTTS voices: {e}")
    if engine == "xtts":
        return {k: v for k, v in result.items() if k.startswith("xtts:")}
    return result


_load_settings()


def get_output_device():
    return _output_device


def set_output_device(device_id):
    global _output_device
    _output_device = device_id


def list_output_devices() -> list:
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        result = []
        for i, dev in enumerate(devices):
            if dev['max_output_channels'] > 0:
                result.append({"id": i, "name": dev['name'], "channels": dev['max_output_channels']})
        return result
    except Exception as e:
        logger.warning(f"Cannot list output devices: {e}")
        return []


def get_xtts_speaker() -> str:
    return _xtts_speaker


def set_xtts_speaker(s: str):
    global _xtts_speaker
    _xtts_speaker = s


def _load_xtts():
    global _xtts
    with _xtts_lock:
        if _xtts is not None:
            return _xtts
        logger.info("Loading XTTS v2 model (this may take ~15s)...")
        orig_input = builtins.input
        builtins.input = lambda prompt='': 'y'
        try:
            from TTS.api import TTS
            import torch
            _xtts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=torch.cuda.is_available())
            logger.info(f"XTTS v2 loaded, {len(_xtts.speakers)} speakers available")
            # Warmup first call to initialize CUDA kernels
            try:
                _xtts.tts(text=".", speaker=_xtts.speakers[0], language="ru")
                logger.info("XTTS warmup done")
            except Exception as we:
                logger.warning(f"XTTS warmup failed (non-critical): {we}")
        except Exception as e:
            logger.error(f"XTTS loading failed: {e}")
            raise
        finally:
            builtins.input = orig_input
        return _xtts


def _get_voices():
    global VOICE_CACHE
    if VOICE_CACHE is not None:
        return VOICE_CACHE
    voices = {}
    if not os.path.isdir(VOICES_DIR):
        VOICE_CACHE = voices
        return voices
    for f in os.listdir(VOICES_DIR):
        if f.endswith(".onnx"):
            name = f[:-5]
            model = os.path.join(VOICES_DIR, f)
            cfg = model + ".json"
            if os.path.exists(cfg):
                voices[name] = (model, cfg)
    VOICE_CACHE = voices
    return voices


def list_voices() -> dict:
    result = {}
    # Always include Piper voices
    for name, (_, cfg) in _get_voices().items():
        result[name] = os.path.basename(cfg)
        child_name = name + "-child"
        result[child_name] = os.path.basename(cfg) + " (detckiy)"
        anime_name = name + "-anime"
        result[anime_name] = os.path.basename(cfg) + " (anime)"
    # Include XTTS speakers only if engine is set to xtts
    if _engine == "xtts":
        try:
            xtts = _load_xtts()
            for spk in xtts.speakers:
                result[f"xtts:{spk}"] = f"XTTS: {spk}"
        except Exception as e:
            logger.warning(f"Cannot list XTTS voices: {e}")
    return result


def _get_duration(wav_path: str) -> float:
    with wave.open(wav_path, 'rb') as w:
        frames = w.getnframes()
        rate = w.getframerate()
        return frames / rate if rate > 0 else 0.0


def generate_speech(text: str, voice: str = DEFAULT_VOICE) -> tuple:
    import tempfile
    
    # Check if voice is XTTS
    if voice.startswith("xtts:"):
        speaker = voice[5:]
        xtts = _load_xtts()
        logger.info(f"XTTS generating: text={text[:50]}... speaker={speaker}")
        audio = xtts.tts(text=text, speaker=speaker, language="ru")
        fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="xtts_", dir=BASE_DIR)
        os.close(fd)
        import soundfile as sf
        sf.write(out_path, audio, 24000)
        duration = _get_duration(out_path)
        logger.info(f"XTTS generated: {duration:.1f}s")
        vol = get_volume()
        if vol < 1.0:
            _scale_wav_volume(out_path, vol)
        return out_path, duration

    # Piper voices
    voices = _get_voices()
    is_child = voice.endswith("-child")
    is_anime = voice.endswith("-anime")
    suffix = "-child" if is_child else "-anime" if is_anime else ""
    parent = voice[:-len(suffix)] if suffix else voice

    if parent not in voices:
        raise ValueError(f"Voice '{voice}' not found. Available: {list(voices.keys())}")

    model_path, config_path = voices[parent]
    logger.info(f"Piper generating: text={text[:50]}... voice={voice}")

    try:
        from piper import PiperVoice
        import numpy as np

        cache_key = f"{model_path}:{config_path}"
        with _piper_voice_cache_lock:
            cached = _piper_voice_cache.get(cache_key)
            if cached is not None:
                piper_voice = cached
            else:
                piper_voice = PiperVoice.load(model_path, config_path=config_path)
                _piper_voice_cache[cache_key] = piper_voice
        chunks = list(piper_voice.synthesize(text))
        audio_parts = [c.audio_float_array for c in chunks if c.audio_float_array is not None]
        if not audio_parts:
            raise RuntimeError("Piper produced no audio")
        audio = np.concatenate(audio_parts)

        fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="speech_", dir=BASE_DIR)
        os.close(fd)
        import wave as wav_mod
        audio_int16 = (audio * 32767).astype(np.int16)
        with wav_mod.open(out_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(piper_voice.config.sample_rate)
            w.writeframes(audio_int16.tobytes())

        duration = _get_duration(out_path)
        logger.info(f"Piper generated: {duration:.1f}s")
    except Exception as e:
        logger.error(f"Piper API failed: {e}, falling back to CLI")
        import subprocess as _sp
        fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="speech_", dir=BASE_DIR)
        os.close(fd)
        cmd = [
            PIPER_EXE,
            "--model", model_path,
            "--config", config_path,
            "--output_file", out_path,
            "--quiet"
        ]
        proc = _sp.Popen(cmd, stdin=_sp.PIPE, stdout=_sp.DEVNULL, stderr=_sp.PIPE)
        stdout, stderr = proc.communicate(input=text.encode("utf-8"), timeout=30)
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace") if stderr else ""
            raise RuntimeError(f"Piper CLI failed (code {proc.returncode}): {err[:200]}")
        if not os.path.exists(out_path):
            raise RuntimeError("Piper CLI produced no output file")
        duration = _get_duration(out_path)
        logger.info(f"Piper CLI generated: {duration:.1f}s")

    vol = get_volume()
    if vol < 1.0:
        _scale_wav_volume(out_path, vol)

    if is_child:
        _pitch_shift_wav(out_path, 2.2)
        duration = _get_duration(out_path)
    elif is_anime:
        _pitch_shift_wav(out_path, 2.8)
        duration = _get_duration(out_path)

    return out_path, duration


def _scale_wav_volume(path: str, factor: float):
    with wave.open(path, 'rb') as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    sampwidth = params.sampwidth
    rate = params.framerate
    fmt = {1: 'b', 2: 'h', 4: 'i'}.get(sampwidth)
    if fmt is None:
        logger.warning(f"Unsupported sample width {sampwidth}, skipping volume")
        return
    count = len(frames) // sampwidth
    samples = struct.unpack(fmt * count, frames)
    max_val = (1 << (sampwidth * 8 - 1)) - 1
    scaled = [max(-max_val - 1, min(max_val, int(s * factor))) for s in samples]
    scaled_fmt = fmt * count
    with wave.open(path, 'wb') as w:
        w.setparams(params)
        w.writeframes(struct.pack(scaled_fmt, *scaled))


def _pitch_shift_wav(path: str, factor: float):
    with wave.open(path, 'rb') as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    nchannels = params.nchannels
    sampwidth = params.sampwidth
    framerate = params.framerate
    nframes = params.nframes
    if sampwidth != 2:
        return
    import array
    samples = array.array('h', frames)
    new_nframes = int(nframes * factor)
    new_rate = int(framerate * factor)
    new_samples = array.array('h', [0]) * new_nframes
    for i in range(new_nframes):
        src = i / factor
        idx = int(src)
        frac = src - idx
        if 1 <= idx < len(samples) - 2:
            s = samples[idx-1] * (-0.5*frac*frac + frac - 0.5*frac*frac*frac)
            s += samples[idx]   * (1.5*frac*frac - 2.5*frac*frac*frac + 1)
            s += samples[idx+1] * (-1.5*frac*frac + 2*frac*frac*frac + 0.5*frac)
            s += samples[idx+2] * (0.5*frac*frac*frac - 0.5*frac*frac)
        elif idx + 1 < len(samples):
            s = samples[idx] * (1 - frac) + samples[idx + 1] * frac
        elif idx < len(samples):
            s = samples[idx]
        else:
            s = 0
        new_samples[i] = max(-32768, min(32767, int(s)))
    # Normalize to prevent clipping
    peak = max(abs(s) for s in new_samples)
    if peak > 30000:
        scale = 30000.0 / peak
        new_samples = array.array('h', [max(-32768, min(32767, int(s * scale))) for s in new_samples])
    with wave.open(path, 'wb') as w:
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(new_rate)
        w.writeframes(new_samples.tobytes())
    logger.info(f"Pitch shifted by {factor:.0%}")


def play_wav_sync(wav_path: str, duration: float):
    """Play WAV and animate mouth. Runs in a background thread."""
    global _speaking
    with _speech_lock:
        _speaking = True

    device = _output_device

    try:
        import sounddevice as sd
        import numpy as np
        import wave as wav_mod
        with wav_mod.open(wav_path, 'rb') as w:
            params = w.getparams()
            frames = w.readframes(w.getnframes())
        sampwidth = params.sampwidth
        dtype = {1: np.int8, 2: np.int16, 4: np.int32}[sampwidth]
        wav_data = np.frombuffer(frames, dtype=dtype)
        sd.play(wav_data, params.framerate, device=device, blocking=False)

        t0 = time.time()
        while time.time() - t0 < duration + 0.3:
            elapsed = time.time() - t0
            phase = elapsed * math.pi * 6
            mouth = 0.5 + 0.5 * math.sin(phase)
            from live2d_display import state
            state.set_mouth_open(mouth)
            time.sleep(0.03)
    except Exception as e:
        logger.error(f"Playback error: {e}")
    finally:
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        from live2d_display import state
        state.set_mouth_open(0.0)
        with _speech_lock:
            _speaking = False


def speak(text: str, voice: str = None) -> str:
    if not voice:
        voice = get_default_voice()
    if not is_enabled():
        return "Speech is disabled"

    # Fallback: if engine is piper but voice is xtts, force piper
    if voice.startswith("xtts:") and _engine != "xtts":
        piper_v = [k for k in list_voices_by_engine("piper")]
        voice = piper_v[0] if piper_v else DEFAULT_VOICE
        logger.warning(f"XTTS voice not available, falling back to '{voice}'")

    is_xtts = voice.startswith("xtts:")
    # For Piper, check executable exists
    if not is_xtts and not os.path.exists(PIPER_EXE):
        return f"Piper not found at {PIPER_EXE}"

    try:
        wav_path, duration = generate_speech(text, voice)
    except Exception as e:
        logger.error(f"Speech generation failed: {e}")
        return f"Speech generation failed: {e}"

    def _play_and_clean():
        try:
            play_wav_sync(wav_path, duration)
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass

    t = threading.Thread(target=_play_and_clean, daemon=True)
    t.start()

    return f"Speaking ({duration:.1f}s): {text[:60]}..."





def is_speaking() -> bool:
    with _speech_lock:
        return _speaking


def stop_speaking():
    global _speaking
    import sounddevice as sd
    sd.stop()
    from live2d_display import state
    state.set_mouth_open(0.0)
    with _speech_lock:
        _speaking = False
