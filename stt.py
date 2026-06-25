import os
import json
import logging
import threading
import time
import queue
import numpy as np

logger = logging.getLogger("STT")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def _read_model_size():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f).get("stt_model", "tiny")
    except Exception:
        return "tiny"

MODEL_SIZE = _read_model_size()
MODEL_DIR = os.path.join(BASE_DIR, "stt_models")

_model = None
_model_lock = threading.Lock()
_listening = False
_listen_thread = None
_transcript_queue = queue.Queue()
_last_transcript = ""
_on_transcript_cb = None
_stream = None
_paused = False

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 5       # seconds per recognition chunk
_VAD_THRESHOLD = 0.002  # RMS threshold (fallback)

# WebRTC VAD
_webrtc_vad = None
VAD_FRAME_MS = 30
VAD_FRAME_SIZE = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)  # 480 samples
VAD_VOICE_RATIO = 0.5  # minimum fraction of voice frames to accept chunk


def _get_webrtc_vad():
    global _webrtc_vad
    if _webrtc_vad is None:
        try:
            import webrtcvad
            _webrtc_vad = webrtcvad.Vad(3)
        except ImportError:
            _webrtc_vad = False
    return _webrtc_vad


def get_vad_threshold() -> float:
    return _VAD_THRESHOLD


def set_vad_threshold(v: float):
    global _VAD_THRESHOLD
    _VAD_THRESHOLD = max(0.0, min(1.0, v))


def _load_model():
    global _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel
        os.makedirs(MODEL_DIR, exist_ok=True)
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        logger.info(f"Loading faster-whisper {MODEL_SIZE} on {device}...")
        _model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute, download_root=MODEL_DIR)
        logger.info(f"Whisper {MODEL_SIZE} loaded")
        return _model


def set_model_size(size: str):
    global _model, MODEL_SIZE
    valid = ("tiny", "base", "small", "medium", "large-v3")
    if size not in valid:
        raise ValueError(f"Model must be one of {valid}")
    with _model_lock:
        MODEL_SIZE = size
        _model = None


def get_model_size() -> str:
    return MODEL_SIZE


def transcribe_file(wav_path: str, lang: str = "ru") -> dict:
    model = _load_model()
    segments, info = model.transcribe(wav_path, language=lang, beam_size=5)
    text = " ".join(seg.text for seg in segments)
    return {"text": text, "language": info.language, "duration": info.duration,
            "language_probability": info.language_probability}


def transcribe(audio: np.ndarray, lang: str = "ru") -> dict:
    model = _load_model()
    segments, info = model.transcribe(audio, language=lang, beam_size=5)
    text = " ".join(seg.text for seg in segments)
    return {"text": text, "language": info.language, "duration": info.duration,
            "language_probability": info.language_probability}


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio ** 2)))


def _has_voice(audio: np.ndarray) -> bool:
    """Check if audio chunk contains voice. Uses WebRTC VAD if available, falls back to RMS threshold."""
    vad = _get_webrtc_vad()
    if vad is False:
        return _rms(audio) >= _VAD_THRESHOLD
    # Convert float32 [-1,1] to int16
    int16_audio = (audio * 32767).astype(np.int16)
    # Split into frames and check each
    total_frames = 0
    voice_frames = 0
    for i in range(0, len(int16_audio) - VAD_FRAME_SIZE + 1, VAD_FRAME_SIZE):
        frame = int16_audio[i:i + VAD_FRAME_SIZE]
        try:
            is_speech = vad.is_speech(frame.tobytes(), SAMPLE_RATE)
            if is_speech:
                voice_frames += 1
            total_frames += 1
        except Exception:
            pass
    if total_frames == 0:
        return False
    ratio = voice_frames / total_frames
    return ratio >= VAD_VOICE_RATIO


def _record_and_transcribe(lang: str = "ru", device_id=None):
    import sounddevice as sd
    logger.info("Microphone listening started")
    audio_buffer = np.array([], dtype='float32')
    
    def callback(indata, frames, time_info, status):
        nonlocal audio_buffer
        if status:
            logger.warning(f"Stream status: {status}")
        audio_buffer = np.append(audio_buffer, indata[:, 0])
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, device=device_id,
                        dtype='float32', callback=callback):
        while _listening:
            if _paused:
                audio_buffer = np.array([], dtype='float32')
                time.sleep(0.1)
                continue
            if len(audio_buffer) >= SAMPLE_RATE * BLOCK_SIZE:
                chunk = audio_buffer[:int(SAMPLE_RATE * BLOCK_SIZE)]
                audio_buffer = audio_buffer[int(SAMPLE_RATE * BLOCK_SIZE):]
                
                # WebRTC VAD: skip if no voice detected
                if not _has_voice(chunk):
                    continue
                
                try:
                    result = transcribe(chunk, lang)
                    text = result["text"].strip()
                    if text:
                        logger.info(f"Recognized: {text}")
                        global _last_transcript
                        _last_transcript = text
                        _transcript_queue.put(text)
                        if _on_transcript_cb:
                            try:
                                _on_transcript_cb(text)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                except Exception as e:
                    logger.error(f"Transcription error: {e}")
            else:
                time.sleep(0.1)
    logger.info("Microphone listening stopped")


def start_listening(lang: str = "ru", device_id=None) -> str:
    global _listening, _listen_thread
    if _listening:
        return "Already listening"
    # Pre-load model before starting mic
    try:
        _load_model()
    except Exception as e:
        return f"Failed to load model: {e}"
    _listening = True
    _listen_thread = threading.Thread(target=_record_and_transcribe,
                                      args=(lang, device_id), daemon=True)
    _listen_thread.start()
    return f"Listening started (lang={lang})"


def stop_listening() -> str:
    global _listening
    _listening = False
    return "Listening stopped"


def is_listening() -> bool:
    return _listening


def pause():
    global _paused
    _paused = True
    logger.info('Microphone paused')


def resume():
    global _paused
    _paused = False
    logger.info('Microphone resumed')


def is_paused() -> bool:
    return _paused


def get_last_transcript() -> str:
    return _last_transcript


def get_transcript(block: bool = True, timeout: float = None) -> str:
    try:
        return _transcript_queue.get(block=block, timeout=timeout)
    except queue.Empty:
        return ""


def set_transcript_cb(cb):
    global _on_transcript_cb
    _on_transcript_cb = cb


def list_audio_devices() -> list:
    import sounddevice as sd
    devices = sd.query_devices()
    result = []
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            result.append({"id": i, "name": dev['name'],
                           "channels": dev['max_input_channels'],
                           "samplerate": int(dev['default_samplerate'] or 16000)})
    return result
