import os
import sys
import logging
import importlib
import importlib.util

logger = logging.getLogger("PlayModes")
_modes = []


def discover():
    global _modes
    _modes = []
    dir_path = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(dir_path)):
        if f.startswith("_") or not f.endswith(".py"):
            continue
        mod_name = f[:-3]
        try:
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join(dir_path, f))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _modes.append({
                "name": getattr(mod, "NAME", mod_name),
                "module": mod,
                "interval": getattr(mod, "INTERVAL", 2500),
                "click_stops": getattr(mod, "CLICK_STOPS", True),
                "escape_stops": getattr(mod, "ESCAPE_STOPS", True),
                "requires_sprite": getattr(mod, "REQUIRES_SPRITE", False),
            })
        except Exception as e:
            logger.warning(f"Failed to load {mod_name}: {e}")


def list_modes(sprite_only=False):
    if not _modes:
        discover()
    if sprite_only:
        return [m for m in _modes if m.get("requires_sprite")]
    return _modes


def get_mode(index):
    modes = list_modes()
    if 0 <= index < len(modes):
        return modes[index]
    return None


def random_mode(sprite_only=False):
    import random
    modes = list_modes(sprite_only=sprite_only)
    return random.choice(modes) if modes else None


def index_of(name):
    modes = list_modes()
    for i, m in enumerate(modes):
        if m["name"] == name:
            return i
    return 0


class ModeContext:
    def __init__(self, window, state):
        self.window = window
        self.state = state
        self.data = {}
