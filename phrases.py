import os
import json
import logging

logger = logging.getLogger("Phrases")

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_PHRASES_PATH = os.path.join(_CONFIG_DIR, "phrases.json")
_cache = {}

def _load():
    global _cache
    if not _cache:
        try:
            with open(_PHRASES_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            _cache = {k: v for k, v in raw.items() if not k.startswith("//") and isinstance(v, (str, list))}
        except Exception as e:
            logger.error(f"Failed to load phrases.json: {e}")
            _cache = {}
    return _cache

def reload():
    global _cache
    _cache = {}
    return _load()

def get(key: str, **kwargs):
    data = _load()
    template = data.get(key)
    if template is None:
        logger.warning(f"Phrase key '{key}' not found in phrases.json")
        return key
    if isinstance(template, list):
        return template
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing format param {e} for phrase '{key}': {template}")
            return template
    return template

def speak(key: str, **kwargs) -> str:
    from tts import speak as tts_speak
    text = get(key, **kwargs)
    tts_speak(text)
    return text
