import os
import sys
import json
import time
import random
import math
import logging
import threading
import traceback
import base64
from datetime import datetime

import OpenGL.GL as gl
import live2d.v3 as live2d

from PIL import Image

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimerEvent
from PyQt6.QtGui import QGuiApplication, QPainter, QPixmap, QImage
from PyQt6.QtWidgets import QApplication

import play_modes

logger = logging.getLogger("Live2DDisplay")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- Sprite model constants ----
SPRITE_DIR = os.path.join(BASE_DIR, "assets/live2d/Nagatoro_sprite")
SPRITE_MAP = {
    'neutral':        'base.png',
    'eyes_closed':    'close_eaes.png',
    'wink_left':      'left_eye.png',
    'wink_right':     'right_eye.png',
    'love':           'love.png',
    'mouth_open':     'open-mouth-only.png',
    'mouth_open_eyes_closed': 'mouth_open_shot_eyes.png',
    'pansu_shot3':    'pansu3.png',
    'pansu_shot2':    'potsu2.png',
    'no_panty':       'no-panty_sensored.png',
}

MODELS = {
    "hiyori": {
        "path": "assets/live2d/Hiyori/hiyori_free_t08.model3.json",
        "type": "live2d",
        "label": "Hiyori (Live2D)",
    },
    "nagatoro_sprite": {
        "path": "assets/live2d/Nagatoro_sprite",
        "type": "sprite",
        "label": "Нагаторо (Спрайт)",
    },
}


def _remove_bg_flood(pil_img):
    if pil_img.mode == 'RGB':
        pil_img = pil_img.convert('RGBA')
    w, h = pil_img.size
    pixels = pil_img.load()
    bg_r, bg_g, bg_b = pixels[0, 0][:3]
    tol = 12
    visited = set()
    stack = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]
    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        if not (0 <= x < w and 0 <= y < h):
            continue
        px = pixels[x, y]
        if abs(px[0]-bg_r) > tol or abs(px[1]-bg_g) > tol or abs(px[2]-bg_b) > tol:
            continue
        visited.add((x, y))
        pixels[x, y] = (px[0], px[1], px[2], 0)
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            stack.append((x+dx, y+dy))
    return pil_img


def _pil_to_qpixmap(pil_img, scale=1.0):
    if scale != 1.0:
        pw, ph = pil_img.size
        pil_img = pil_img.resize((int(pw * scale), int(ph * scale)), Image.Resampling.LANCZOS)
    if pil_img.mode != 'RGBA':
        pil_img = pil_img.convert('RGBA')
    data = pil_img.tobytes()
    qimg = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


def _load_sprite_frames():
    frames = {}
    if not os.path.isdir(SPRITE_DIR):
        logger.error(f"Sprite directory not found: {SPRITE_DIR}")
        return frames
    for em_name, filename in SPRITE_MAP.items():
        path = os.path.join(SPRITE_DIR, filename)
        if not os.path.exists(path):
            logger.warning(f"Sprite not found: {path}")
            continue
        try:
            pil = Image.open(path).convert('RGBA')
            pil = _remove_bg_flood(pil)
            pix = _pil_to_qpixmap(pil)
            if pix and not pix.isNull():
                frames[em_name] = pix
            else:
                logger.error(f"Null pixmap for {em_name}")
        except Exception as e:
            logger.error(f"Failed to load sprite {em_name}: {e}")
            traceback.print_exc()
    return frames


def global_excepthook(exc_type, exc_value, exc_traceback):
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    # Don't call sys.__excepthook__ which shows dialog on Windows


sys.excepthook = global_excepthook


class CharacterState:
    def __init__(self):
        self._lock = threading.Lock()
        self.emotion = "neutral"
        self.mouth_open = 0.0
        self.eye_x = 0.0
        self.eye_y = 0.0
        self.visible = True
        self.param_overrides = {}
        self._pending_motion = None
        self.render_mode = "live2d"
        self.model_name = "hiyori"

    def play_motion(self, group: str, no: int = 0, priority: int = 2):
        with self._lock:
            self._pending_motion = (group, no, priority)

    def consume_motion(self):
        with self._lock:
            m = self._pending_motion
            self._pending_motion = None
            return m

    def set_emotion(self, emotion: str):
        with self._lock:
            self.emotion = emotion

    def get_emotion(self) -> str:
        with self._lock:
            return self.emotion

    def set_mouth_open(self, value: float):
        with self._lock:
            self.mouth_open = max(0.0, min(1.0, value))

    def get_mouth_open(self) -> float:
        with self._lock:
            return self.mouth_open

    def set_eye_pos(self, x: float, y: float):
        with self._lock:
            self.eye_x = max(-1.0, min(1.0, x))
            self.eye_y = max(-1.0, min(1.0, y))

    def get_eye_pos(self):
        with self._lock:
            return self.eye_x, self.eye_y

    def set_param(self, name: str, value: float):
        with self._lock:
            self.param_overrides[name] = value

    def get_params(self):
        with self._lock:
            return dict(self.param_overrides)

    def set_visible(self, v: bool):
        with self._lock:
            self.visible = v

    def is_visible(self) -> bool:
        with self._lock:
            return self.visible

    def set_render_mode(self, mode: str):
        with self._lock:
            self.render_mode = mode

    def get_render_mode(self) -> str:
        with self._lock:
            return self.render_mode

    def set_model_name(self, name: str):
        with self._lock:
            self.model_name = name

    def get_model_name(self) -> str:
        with self._lock:
            return self.model_name

    def reset(self):
        with self._lock:
            self.emotion = "neutral"
            self.mouth_open = 0.0
            self.eye_x = 0.0
            self.eye_y = 0.0
            self.param_overrides.clear()
            self._pending_motion = None


state = CharacterState()
game_invite_text = "Давай поиграем!"


def _resolve_path(config_path: str) -> str:
    if os.path.isabs(config_path):
        return config_path
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(base, config_path))


GAMES = [
    {"id": "hide_seek",    "name": "Прятки",      "icon": "🙈", "start_text": "Давай поиграем в прятки! Найди меня!",             "emotion": "surprise", "timed": False},
    {"id": "tag",          "name": "Щелчок",      "icon": "👆", "start_text": "Давай поиграем! Щёлкни по мне!",                    "emotion": "joy",      "timed": False},
    {"id": "dance",        "name": "Танцы",       "icon": "💃", "start_text": "Потанцуем! Повторяй за мной!",                      "emotion": "joy",      "timed": True,  "interval": 2000},
    {"id": "compliment",   "name": "Комплимент",  "icon": "💖", "start_text": "Я скажу тебе кое-что приятное!",                    "emotion": "love",     "timed": False},
    {"id": "emotion_game", "name": "Угадай эмоцию", "icon": "🤔", "start_text": "Давай поиграем! Угадай мою эмоцию!",             "emotion": "neutral",  "timed": False},
    {"id": "mimic",        "name": "Повторялка",   "icon": "🔄", "start_text": "Давай поиграем! Повторяй за мной!",               "emotion": "amusement","timed": False},
    {"id": "pansu_click",  "name": "Пансу Клик",   "icon": "👙", "start_text": "Хочешь сыграть в Пансу Клик?",                    "emotion": "love",     "timed": True,  "interval": 1000, "requires_sprite": True},
]

DEFAULT_GAME_TEXTS = {g["id"]: g["start_text"] for g in GAMES}


class Live2DDisplayWindow(QOpenGLWidget):
    def __init__(self, model_path: str, config: dict, parent=None):
        super().__init__()
        self.config = config
        self.model_path = model_path

        self.resize(config.get("window_width", 400), config.get("window_height", 600))
        self.setWindowTitle("MCP Live2D Companion")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        try:
            live2d.init()
        except Exception as e:
            logger.error(f"live2d.init failed: {e}")

        self.live2d_model = None
        self.model_loaded = False
        self.opengl_ready = False
        self.timer_id = None

        self._sprite_frames = _load_sprite_frames()
        self._sprite_emotion = "neutral"
        self._sprite_loaded = False
        self._sprite_blink_next = 0.0
        self._pending_model_switch = None
        self._switch_signal = None

        self.dragging_window = False
        self.drag_offset = QtCore.QPoint()

        self._cursor_timer = QtCore.QTimer()
        self._cursor_timer.timeout.connect(self._update_eye_tracking)
        self._cursor_timer.start(50)

        self._wink_next_time = 0.0
        self._wink_eye = 0
        self._wink_start_time = 0.0
        self._wink_duration = 0.15

        self._dance_time = 0.0

        self._walk_start_time = 0.0
        self._walk_duration = 3.0
        self._walk_active = False
        self._walk_from = QtCore.QPoint()
        self._walk_to = QtCore.QPoint()

        self._press_pos = None

        self._play_active = False
        self._play_pattern = 0
        self._play_timer = QtCore.QTimer()
        self._play_timer.timeout.connect(self._play_tick)
        self._mode_ctx = None

        self._game_active = None
        self._game_step = 0
        self._game_timer = QtCore.QTimer()
        self._game_timer.timeout.connect(self._game_tick)

        self._live_active = False
        self._live_timer = QtCore.QTimer()
        self._live_timer.timeout.connect(self._live_tick)

        self._music_mode_active = False
        self._favorite_tracks = set(config.get("favorite_tracks", []))

        import alarm_timer
        alarm_timer.set_trigger_callback(self._on_alarm_timer_cfg_change)
        self._alarm_triggered = False
        self._timer_triggered = False
        self._mcp_alarm_triggered = False
        self._mcp_timer_triggered = False
        self._alarm_timer_checker = QtCore.QTimer()
        self._alarm_timer_checker.timeout.connect(self._check_alarm_timer)
        self._alarm_timer_checker.start(1000)
        self._at_firing = False
        self._at_data = None
        self._at_repeat_count = 0
        self._at_cfg_signal = QtCore.QTimer()
        self._at_cfg_signal.setSingleShot(True)
        self._at_cfg_signal.timeout.connect(self._on_at_cfg_queue)
        self._prev_at_cfg = alarm_timer.get_settings()

        self._screenshot_result = None
        self._screenshot_event = threading.Event()
        self._screenshot_delay = 0

        self._click_count = 0
        self._click_timer = QtCore.QTimer()
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_click_timer)
        self._click_times = []
        self._rapid_triggered = set()
        self._rapid_session_start = 0.0
        self._rapid_emotion_timer = QtCore.QTimer()
        self._rapid_emotion_timer.timeout.connect(self._rapid_emotion_tick)
        self._climax_active = False
        self._climax_end = 0.0
        self._climax_block_clicks = True
        self._climax_timer = None
        self._climax_phrase_block = False
        self._click_once_done = set()
        self._rc_block = False
        self._rc_escape_active = False
        self._rc_escape_timer = None
        self._rc_escape_phase = 0
        self._rc_escape_counter = 0
        self._last_drag_speak = 0.0
        self._drag_session_count = 0

        self._hide_anim_active = False
        self._hide_anim_start = 0.0
        self._hide_anim_duration = 3.0
        self._hide_anim_from = QtCore.QPoint()
        self._hide_anim_to = QtCore.QPoint()
        self._hide_anim_opacity_from = 1.0
        self._hide_anim_callback = None

        self._show_anim_active = False
        self._show_anim_start = 0.0
        self._show_anim_duration = 1.2
        self._show_anim_wave_done = False

        self._exit_anim_active = False
        self._exit_anim_start = 0.0
        self._exit_anim_duration = 2.0
        self._exit_anim_from = QtCore.QPoint()
        self._exit_anim_to = QtCore.QPoint()
        self._anim_locked = False
        self._trapped_active = False
        self._trapped_start = 0.0
        self._trapped_duration = 4.0

        global game_invite_text
        game_invite_text = self.config.get("game_invite_text", "Давай поиграем!")

        self._tray = QtWidgets.QSystemTrayIcon(self)
        self._tray.setToolTip("Live2D Companion")
        self._tray_frames = []
        for scale in [1.0, 1.3, 1.0, 0.8]:
            sz = 48
            heart = QtGui.QPixmap(sz, sz)
            heart.fill(QtCore.Qt.GlobalColor.transparent)
            p = QtGui.QPainter(heart)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            p.setBrush(QtGui.QColor("#FF1493"))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            cx, cy = sz // 2, sz // 2
            r = int(8 * scale)
            p.drawEllipse(int(cx - r * 1.5), int(cy - r * 1.2), r * 2, r * 2)
            p.drawEllipse(int(cx - r * 0.5), int(cy - r * 1.2), r * 2, r * 2)
            poly = QtGui.QPolygonF([
                QtCore.QPointF(cx - r * 1.8, cy - r * 0.2),
                QtCore.QPointF(cx, cy + r * 1.5),
                QtCore.QPointF(cx + r * 1.8, cy - r * 0.2)
            ])
            p.drawPolygon(poly)
            p.end()
            self._tray_frames.append(QtGui.QIcon(heart))
        self._tray.setIcon(self._tray_frames[0])
        self._tray_frame_idx = 0
        self._tray_timer = QtCore.QTimer()
        self._tray_timer.timeout.connect(self._tray_tick)
        self._tray_timer.start(600)
        tray_menu = QtWidgets.QMenu()
        act_show = tray_menu.addAction("Show Companion")
        act_show.triggered.connect(self._show_from_tray)
        act_screenshot = tray_menu.addAction("📸 Screenshot")
        act_screenshot.triggered.connect(self._take_screenshot_action)
        tray_menu.addSeparator()
        tray_model_menu = tray_menu.addMenu("🔄 Model")
        self._tray_model_actions = {}
        for mk, mv in MODELS.items():
            ma = tray_model_menu.addAction(mv['label'])
            ma.setCheckable(True)
            ma.setChecked(mk == "hiyori")
            ma.setData(mk)
            self._tray_model_actions[mk] = ma
            ma.triggered.connect(lambda checked, m=mk: self.switch_model(m))
        tray_menu.addSeparator()
        act_exit = tray_menu.addAction("Exit")
        act_exit.triggered.connect(self._start_exit_animation)
        self._tray.setContextMenu(tray_menu)
        self._tray.show()

    def initializeGL(self):
        if self.opengl_ready:
            return
        try:
            self.makeCurrent()
            if live2d.LIVE2D_VERSION == 3:
                live2d.glInit()
            self.opengl_ready = True
            if not self.model_loaded:
                self._do_load_model(self.model_path)
        except Exception as e:
            logger.error(f"initializeGL failed: {e}")
            self.opengl_ready = True  # prevent retry

    def _do_load_model(self, path: str):
        try:
            try:
                self.makeCurrent()
            except Exception:
                pass
            if self.live2d_model:
                try:
                    self.live2d_model = None
                except Exception:
                    pass
                self.model_loaded = False

            self.live2d_model = live2d.LAppModel()
            self.live2d_model.SetAutoBreathEnable(True)
            self.live2d_model.SetAutoBlinkEnable(True)
            self.live2d_model.LoadModelJson(path)

            w, h = self.width(), self.height()
            self.live2d_model.Resize(w, h)
            self.model_loaded = True
            state.reset()

            if self.timer_id:
                self.killTimer(self.timer_id)
            fps = self.config.get("fps", 30)
            self.timer_id = self.startTimer(int(1000 / fps))

            self.setWindowTitle("Live2D - Hiyori")
            QtCore.QTimer.singleShot(100, self._start_walk_in)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.live2d_model = None
            self.model_loaded = False

    def resizeGL(self, w: int, h: int):
        try:
            if self.live2d_model:
                self.live2d_model.Resize(w, h)
        except Exception as e:
            logger.debug(f"resizeGL error: {e}")

    def paintGL(self):
        try:
            if state.get_render_mode() == "sprite" and self._sprite_loaded:
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                p.fillRect(self.rect(), Qt.GlobalColor.transparent)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                self._sprite_emotion = self._resolve_sprite_emotion()
                pix = self._sprite_frames.get(self._sprite_emotion)
                if pix:
                    scaled = pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    x = (self.width() - scaled.width()) // 2
                    y = (self.height() - scaled.height()) // 2
                    p.drawPixmap(x, y, scaled)
                p.end()
            else:
                gl.glClearColor(0.0, 0.0, 0.0, 0.0)
                gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
                if self.live2d_model:
                    self.live2d_model.Update()
                    self._apply_state()
                    self.live2d_model.Draw()
        except Exception as e:
            logger.debug(f"paintGL error: {e}")

    def _resolve_sprite_emotion(self) -> str:
        mouth = state.get_mouth_open()
        em = state.get_emotion()
        if mouth > 0.1:
            if em in ('eyes_closed', 'wink_left', 'wink_right') and "mouth_open_eyes_closed" in self._sprite_frames:
                return "mouth_open_eyes_closed"
            if "mouth_open" in self._sprite_frames:
                if em not in ('pansu_shot2', 'pansu_shot3', 'no_panty'):
                    return "mouth_open"
        if em in self._sprite_frames:
            return em
        return "neutral"

    def _sprite_blink_tick(self):
        now = time.time()
        if now < self._sprite_blink_next:
            return
        _blinks = ['wink_left', 'wink_right', 'eyes_closed']
        blink = random.choice(_blinks)
        if blink in self._sprite_frames:
            state.set_emotion(blink)
        self._sprite_blink_next = now + random.uniform(3.0, 6.0)
        # Reset blink after short duration via single-shot
        QtCore.QTimer.singleShot(250, self._sprite_blink_reset)

    def _sprite_blink_reset(self):
        if state.get_render_mode() == "sprite" and state.get_emotion() in ('wink_left', 'wink_right', 'eyes_closed'):
            state.set_emotion("neutral")

    def switch_model(self, model_name: str) -> str:
        """Switch between models: 'hiyori' or 'nagatoro_sprite'.
        Thread-safe: queues switch via timer for main thread execution.
        """
        if model_name not in MODELS:
            return f"Error: Unknown model '{model_name}'. Available: {list(MODELS.keys())}"

        if threading.current_thread() is not threading.main_thread():
            self._pending_model_switch = model_name
            logger.info(f"switch_model: queued {model_name}, pending={self._pending_model_switch}, timer_id={self.timer_id}")
            return f"Switching to: {MODELS[model_name]['label']}"

        return self._execute_switch(model_name)

    def timerEvent(self, a0: QTimerEvent | None):
        try:
            if self._pending_model_switch:
                model_name = self._pending_model_switch
                self._pending_model_switch = None
                logger.info(f"Processing switch to {model_name}")
                try:
                    result = self._execute_switch(model_name)
                    logger.info(f"Model switch result: {result}")
                except Exception as e:
                    logger.error(f"Model switch failed: {e}")
                    traceback.print_exc()
            if state.get_render_mode() == "sprite":
                self._sprite_blink_tick()
            self._apply_state()
            self.update()
        except Exception as e:
            logger.error(f"timerEvent error: {e}", exc_info=True)

    def _update_tray_model_checks(self, current_model: str):
        if hasattr(self, '_tray_model_actions'):
            for mk, ma in self._tray_model_actions.items():
                ma.setChecked(mk == current_model)

    def _execute_switch(self, model_name: str) -> str:
        model_cfg = MODELS[model_name]

        if self.live2d_model:
            try:
                self.live2d_model = None
            except Exception:
                pass
            self.model_loaded = False

        self._sprite_loaded = False

        if model_cfg["type"] == "live2d":
            path = _resolve_path(model_cfg["path"])
            if not os.path.exists(path):
                return f"Error: Model file not found: {path}"
            try:
                self.makeCurrent()
            except Exception:
                pass
            self._do_load_model(path)
            state.set_render_mode("live2d")
            state.set_model_name(model_name)
            self.setWindowTitle(f"Live2D - {model_cfg['label']}")
            self.resize(self.config.get("window_width", 400), self.config.get("window_height", 600))
        elif model_cfg["type"] == "sprite":
            if not self._sprite_frames:
                return "Error: No sprite frames loaded"
            self._sprite_loaded = True
            self._sprite_emotion = "neutral"
            self._sprite_blink_next = time.time() + random.uniform(3.0, 6.0)
            state.reset()
            state.set_render_mode("sprite")
            state.set_model_name(model_name)
            state.set_emotion("neutral")
            self.setWindowTitle(f"Live2D - {model_cfg['label']}")
            self.resize(500, 600)

            if self.timer_id:
                self.killTimer(self.timer_id)
            fps = self.config.get("fps", 30)
            self.timer_id = self.startTimer(int(1000 / fps))

        self._update_tray_model_checks(model_name)
        return f"Switched to: {model_cfg['label']}"

    def _start_walk_in(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        sw, sh = screen.width(), screen.height()
        ctr_x = (sw - self.width()) // 2
        ctr_y = (sh - self.height()) // 2
        self.move(ctr_x, ctr_y)
        self._walk_from = QtCore.QPoint(ctr_x, ctr_y)
        self._walk_to = QtCore.QPoint(sw - self.width() - 20, sh - self.height() - 100)
        self._walk_start_time = time.time()
        self._walk_active = True

    def _apply_state(self):
        render_mode = state.get_render_mode()

        # ----- Live2D specific calls -----
        if render_mode == "live2d" and self.live2d_model:
            motion = state.consume_motion()
            if motion:
                try:
                    self.live2d_model.StartMotion(motion[0], motion[1], motion[2])
                except Exception as e:
                    logger.debug(f"StartMotion error: {e}")

            emotion = state.get_emotion()
            if emotion != getattr(self, '_last_emotion', None):
                self._last_emotion = emotion
                try:
                    self.live2d_model.SetExpression(emotion)
                except Exception as e:
                    logger.debug(f"SetExpression error: {e}")

            try:
                self.live2d_model.SetParameterValue("ParamMouthOpenY", state.get_mouth_open())
            except Exception:
                pass

            self._update_dance()
            self._update_wink()

            ex, ey = state.get_eye_pos()
            try:
                self.live2d_model.SetParameterValue("ParamEyeBallX", ex)
                self.live2d_model.SetParameterValue("ParamEyeBallY", ey)
            except Exception:
                pass

            for name, val in state.get_params().items():
                try:
                    self.live2d_model.SetParameterValue(name, val)
                except Exception:
                    pass

        # ----- Sprite specific -----
        if render_mode == "sprite":
            state.consume_motion()

        # ----- Common animation updates -----
        self._update_walk()
        self._update_hide_anim()
        self._update_show_anim()
        self._update_exit_anim()
        self._update_trapped_anim()

        visible = state.is_visible()
        if visible != self.isVisible():
            if visible:
                self.show()
            else:
                self.hide()

    def _greet_startup(self):
        try:
            import tts
            if not tts.is_enabled():
                return
            import phrases
            phrases.speak("greeting_startup")
        except Exception:
            pass

    def _tray_tick(self):
        self._tray_frame_idx = (self._tray_frame_idx + 1) % len(self._tray_frames)
        self._tray.setIcon(self._tray_frames[self._tray_frame_idx])

    def _start_hide_animation(self):
        if self._anim_locked:
            return
        self._anim_locked = True
        import phrases
        phrases.speak("hide_animation")
        self._hide_anim_from = QtCore.QPoint(self.pos())
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self._hide_anim_to = QtCore.QPoint(screen.width() - 50, screen.height() - 50)
        self._hide_anim_opacity_from = self.windowOpacity()
        self._hide_anim_start = time.time()
        self._hide_anim_active = True

    def _update_hide_anim(self):
        if not self._hide_anim_active:
            return
        elapsed = time.time() - self._hide_anim_start
        if elapsed >= self._hide_anim_duration:
            self._hide_anim_active = False
            self._anim_locked = False
            self.move(self._hide_anim_to)
            self.setWindowOpacity(0.0)
            state.set_visible(False)
            self.hide()
            self.setWindowOpacity(self._hide_anim_opacity_from)
            return
        t = elapsed / self._hide_anim_duration
        t = t * t * (3 - 2 * t)
        x = self._hide_anim_from.x() + (self._hide_anim_to.x() - self._hide_anim_from.x()) * t
        y = self._hide_anim_from.y() + (self._hide_anim_to.y() - self._hide_anim_from.y()) * t
        self.move(int(x), int(y))
        base_opacity = self._hide_anim_opacity_from * (1 - t * t)
        flicker = 1.0 - 0.25 * (math.sin(t * math.pi * 30) * 0.5 + 0.5)
        self.setWindowOpacity(max(0.0, base_opacity * flicker))

    def _start_trapped_animation(self):
        state.set_visible(True)
        self.show()
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 100)
        self.setWindowOpacity(1.0)
        self.raise_()
        state.set_emotion("fear")
        import phrases
        phrases.speak("trapped_animation")
        self._trapped_start = time.time()
        self._trapped_duration = 4.0
        self._trapped_active = True

    def _update_trapped_anim(self):
        if not self._trapped_active:
            return
        elapsed = time.time() - self._trapped_start
        if elapsed >= self._trapped_duration:
            self._trapped_active = False
            self._start_hide_animation()
            return
        flicker = 1.0 - 0.3 * (math.sin(elapsed * math.pi * 25) * 0.5 + 0.5)
        self.setWindowOpacity(max(0.0, flicker))

    def _show_from_tray(self):
        if self._at_firing:
            self._stop_alarm_timer_mode()
        if self._play_active:
            self._stop_play()
        state.set_visible(True)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 100)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        import phrases
        phrases.speak("show_animation")
        state.play_motion("Tap", 0, 2)
        self._show_anim_start = time.time()
        self._show_anim_active = True
        self._show_anim_wave_done = False

    def _update_show_anim(self):
        if not self._show_anim_active:
            return
        elapsed = time.time() - self._show_anim_start
        if elapsed >= self._show_anim_duration:
            self._show_anim_active = False
            self._anim_locked = False
            self.setWindowOpacity(1.0)
            return
        t = elapsed / self._show_anim_duration
        self.setWindowOpacity(min(1.0, t * t * (3 - 2 * t)))
        if t > 0.5 and not self._show_anim_wave_done:
            self._show_anim_wave_done = True
            state.play_motion("Flick", 0, 2)

    def _start_exit_animation(self):
        if self._anim_locked:
            return
        self._anim_locked = True
        import phrases
        phrases.speak("exit_animation")
        self._exit_anim_from = QtCore.QPoint(self.pos())
        self._exit_anim_to = QtCore.QPoint(-self.width(), self.pos().y())
        self._exit_anim_active = False
        self._check_exit_tts()

    def _check_exit_tts(self):
        import tts
        if tts.is_speaking():
            QtCore.QTimer.singleShot(100, self._check_exit_tts)
        else:
            self._exit_anim_start = time.time()
            self._exit_anim_active = True

    def _update_exit_anim(self):
        if not self._exit_anim_active:
            return
        elapsed = time.time() - self._exit_anim_start
        if elapsed >= self._exit_anim_duration:
            self._exit_anim_active = False
            self._anim_locked = False
            self.close()
            QApplication.quit()
            return
        t = elapsed / self._exit_anim_duration
        t = t * t * (3 - 2 * t)
        x = self._exit_anim_from.x() + (self._exit_anim_to.x() - self._exit_anim_from.x()) * t
        y = self._exit_anim_from.y() + (self._exit_anim_to.y() - self._exit_anim_from.y()) * t
        self.move(int(x), int(y))
        flicker = 1.0 - 0.3 * (math.sin(t * math.pi * 20) * 0.5 + 0.5) if t > 0.3 else 1.0
        self.setWindowOpacity(max(0.0, flicker))

    def _update_walk(self):
        if not self._walk_active:
            return
        elapsed = time.time() - self._walk_start_time
        if elapsed >= self._walk_duration:
            self._walk_active = False
            self.move(self._walk_to)
            try:
                self.live2d_model.SetParameterValue("ParamBodyAngleZ", 0.0)
            except Exception:
                pass
            QtCore.QTimer.singleShot(500, self._greet_startup)
            return
        t = elapsed / self._walk_duration
        t = t * t * (3 - 2 * t)
        x = self._walk_from.x() + (self._walk_to.x() - self._walk_from.x()) * t
        y = self._walk_from.y() + (self._walk_to.y() - self._walk_from.y()) * t
        self.move(int(x), int(y))
        tilt = (t - 0.5) * 10
        try:
            self.live2d_model.SetParameterValue("ParamBodyAngleZ", tilt)
        except Exception:
            pass

    def _update_wink(self):
        now = time.time()
        if self._wink_start_time > 0:
            if now - self._wink_start_time >= self._wink_duration:
                try:
                    self.live2d_model.SetParameterValue("ParamEyeLOpen", 1.0)
                    self.live2d_model.SetParameterValue("ParamEyeROpen", 1.0)
                except Exception:
                    pass
                self._wink_start_time = 0.0
                self._wink_next_time = now + random.uniform(3.0, 6.0)
            return
        if now >= self._wink_next_time:
            self._wink_start_time = now
            if self._wink_eye == 0:
                try:
                    self.live2d_model.SetParameterValue("ParamEyeLOpen", 0.0)
                except Exception:
                    pass
            else:
                try:
                    self.live2d_model.SetParameterValue("ParamEyeROpen", 0.0)
                except Exception:
                    pass
            self._wink_eye = 1 - self._wink_eye

    def _update_dance(self):
        try:
            import music_player
            if not music_player.is_playing():
                self._dance_time = 0.0
                return
            if not self.live2d_model:
                return
            dt = 1.0 / self.config.get("fps", 30)
            self._dance_time += dt
            speed = 2.0
            sway = 5.0
            body_z = sway * math.sin(self._dance_time * speed)
            body_x = 3.0 * math.sin(self._dance_time * speed * 1.3)
            body_y = 2.0 * math.sin(self._dance_time * speed * 0.7)
            self.live2d_model.SetParameterValue("ParamBodyAngleZ", body_z)
            self.live2d_model.SetParameterValue("ParamBodyAngleX", body_x)
            self.live2d_model.SetParameterValue("ParamBodyAngleY", body_y)
            self.live2d_model.SetParameterValue("ParamMouthOpenY", 0.3)
        except Exception:
            pass

    def _update_eye_tracking(self):
        try:
            if not self.live2d_model:
                return
            cursor = QtGui.QCursor.pos()
            widget_center = self.geometry().center()
            dx = (cursor.x() - widget_center.x()) / (self.width() / 2)
            dy = (cursor.y() - widget_center.y()) / (self.height() / 2)
            dx = max(-1.0, min(1.0, dx))
            dy = max(-1.0, min(1.0, dy))
            self.live2d_model.SetParameterValue("ParamAngleX", dx * 15)
            self.live2d_model.SetParameterValue("ParamAngleY", -dy * 15)
        except Exception as e:
            logger.debug(f"eye_tracking error: {e}")

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.dragging_window = True
                self._press_pos = event.globalPosition().toPoint()
                self.drag_offset = self._press_pos - self.frameGeometry().topLeft()
                if self._play_active and self._mode_ctx:
                    mode = play_modes.get_mode(self._play_pattern)
                    if mode and hasattr(mode["module"], "mouse_down"):
                        try:
                            mode["module"].mouse_down(self._mode_ctx)
                        except Exception:
                            pass
        except Exception:
            pass

    def mouseMoveEvent(self, event):
        try:
            if self.dragging_window:
                self.move(event.globalPosition().toPoint() - self.drag_offset)
                now = time.time()
                if now - self._last_drag_speak > 1.5:
                    self._last_drag_speak = now
                    import phrases
                    text = phrases.get("drag_sound")
                    if text:
                        phrases.speak("drag_sound")
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                if self._game_active:
                    self._game_double_click()
                    return
                if self._play_active and self._mode_ctx:
                    mode = play_modes.get_mode(self._play_pattern)
                    if mode and hasattr(mode["module"], "double_click"):
                        try:
                            mode["module"].double_click(self._mode_ctx)
                            return
                        except Exception:
                            pass
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.dragging_window = False
                if self._play_active and self._mode_ctx:
                    mode = play_modes.get_mode(self._play_pattern)
                    if mode and hasattr(mode["module"], "mouse_up"):
                        try:
                            mode["module"].mouse_up(self._mode_ctx)
                        except Exception:
                            pass
                if self._press_pos:
                    dist = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
                    if dist >= 10:
                        self._drag_session_count += 1
                        import alarm_timer
                        threshold = alarm_timer.get_settings().get("drag_phrase_threshold", 10)
                        if self._drag_session_count >= threshold:
                            self._drag_session_count = 0
                            import phrases
                            import random
                            pool = phrases.get("drag_phrases")
                            if isinstance(pool, list) and pool:
                                text = random.choice(pool)
                                from tts import speak as tts_speak
                                tts_speak(text)
                    else:
                        self._react_click()
                else:
                    self._react_click()
                self._press_pos = None
        except Exception:
            pass

    def keyPressEvent(self, event):
        if self._at_firing:
            self._stop_alarm_timer_mode()
        elif event.key() == Qt.Key.Key_Escape and self._play_active:
            mode = play_modes.get_mode(self._play_pattern)
            if mode and not mode["escape_stops"]:
                return
            self._stop_play()
        super().keyPressEvent(event)

    def _react_click(self):
        if self._rc_escape_active:
            return
        if self._rc_block:
            import tts
            if tts.is_speaking():
                return
            self._rc_block = False
        if self._climax_active and getattr(self, '_climax_block_clicks', False):
            return
        if self._climax_phrase_block:
            import tts
            if tts.is_speaking():
                return
            self._climax_phrase_block = False
            self._start_climax()
        now = time.time()
        self._click_times.append(now)
        if len(self._click_times) > 200:
            self._click_times = self._click_times[-200:]

        self._check_rapid_click()

        if self._at_firing:
            self._at_click()
            return
        if getattr(self, '_missed_alarm_pending', False):
            self._missed_alarm_pending = False
            import tts
            tts.speak(self._missed_alarm_text)
            return
        if self._play_active:
            mode = play_modes.get_mode(self._play_pattern)
            if mode and not mode["click_stops"]:
                if hasattr(mode["module"], "click"):
                    try:
                        mode["module"].click(self._mode_ctx)
                    except Exception:
                        pass
                return
            logger.info("Click stopped play mode")
            self._stop_play()
            return
        if self._game_active:
            self._react_click_game()
            return

        self._click_count += 1
        self._click_timer.start(400)

    def _check_rapid_click(self):
        import alarm_timer
        cfg = alarm_timer.get_settings()
        threshold = cfg.get("rapid_click_threshold", 5)
        window = cfg.get("rapid_click_window", 2.0)

        now = time.time()
        cutoff = now - window
        recent = [t for t in self._click_times if t > cutoff]

        if len(recent) >= threshold:
            if self._rapid_session_start == 0:
                self._rapid_session_start = recent[0]
                self._rapid_triggered.clear()
            elapsed = now - self._rapid_session_start
            import phrases

            times = cfg.get("rapid_click_times", [60, 30, 20, 10, 3])
            triggered = None
            for t_sec in times:
                key = f"rapid_{t_sec}s"
                if elapsed >= t_sec and key not in self._rapid_triggered:
                    triggered = (t_sec, key)
                    break
            if triggered:
                t_sec, key = triggered
                self._rapid_triggered.add(key)
                text = phrases.get(key)
                if text:
                    phrases.speak(key)
                emotions = cfg.get("rapid_emotions",
                    ["joy", "surprise", "amusement", "love", "fear", "sad"])
                motions = cfg.get("rapid_motions",
                    ["Tap", "Flick", "FlickDown", "Tap@Body"])
                state.set_emotion(random.choice(emotions))
                state.play_motion(random.choice(motions), 0, 2)
                state.set_param("ParamBodyAngleZ", random.uniform(-12, 12))
                if key == "rapid_60s":
                    self._climax_phrase_block = True
                if t_sec >= 30:
                    self._rapid_emotion_timer.start(500)
                return
        else:
            self._rapid_session_start = 0
            self._rapid_triggered.clear()
            self._rapid_emotion_timer.stop()

    def _on_click_timer(self):
        count = min(self._click_count, 3)
        self._click_count = 0
        self._check_rapid_click()
        self._speak_random_click()
        key = f"click_{count}"
        import phrases
        text = phrases.get(key)
        if count >= 1 and count <= 3 and text and key not in self._click_once_done:
            self._click_once_done.add(key)
            phrases.speak(key)
        emotions = ["joy", "surprise", "love", "amusement"]
        motions = ["Tap", "Flick", "FlickDown"]
        emotion = random.choice(emotions)
        motion = random.choice(motions)
        state.set_emotion(emotion)
        state.play_motion(motion, 0, 2)
        tilt = random.uniform(-8, 8)
        state.set_param("ParamBodyAngleZ", tilt)
        logger.info(f"Click reaction: emotion={emotion}, motion={motion}")

    def _game_speak(self, text=None):
        msg = text if text else game_invite_text
        try:
            import tts
            tts.speak(msg)
        except Exception:
            pass

    def _start_game(self, gid):
        if self._play_active:
            self._stop_play()
        self._game_active = gid
        self._game_step = 0
        self._pc_confirm_timer = QtCore.QTimer()
        self._pc_confirm_timer.setSingleShot(True)
        self._pc_confirm_timer.timeout.connect(self._pc_check_answer)
        game = next((g for g in GAMES if g["id"] == gid), None)
        if not game:
            return
        start = game.get("start_text")
        try:
            with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
                cfg = json.load(f)
            stored = cfg.get("game_texts", {})
            if gid in stored:
                start = stored[gid]
        except Exception:
            pass
        if gid == "pansu_click":
            state.set_visible(False)
            self.hide()
            self._game_step = 0
            self._pc_countdown = 0
            self._pc_round = 0
            self._pc_pansu_count = 0
            self._pc_shots = []
            self._pc_answer = 0
            self._pc_center_x = 0
            self._pc_center_y = 0
            self._pc_rules_spoken = False
            self._game_timer.start(1000)
            logger.info("Pansu Click game started")
            return
        self._game_speak(start)
        state.set_emotion(game.get("emotion", "joy"))
        state.play_motion("Tap", 0, 2)
        logger.info(f"Game started: {game['name']}")
        if game.get("timed"):
            self._game_timer.start(game["interval"])

    def _game_double_click(self):
        if self._game_active == "pansu_click":
            if self._game_step == 1:
                self._game_step = 2
                self._pc_countdown = 0
                screen = QGuiApplication.primaryScreen().availableGeometry()
                self._pc_center_x = (screen.width() - self.width()) // 2
                self._pc_center_y = (screen.height() - self.height()) // 2
                self.move(self._pc_center_x, -self.height())
                state.set_mouth_open(0.0)
                state.set_emotion("love")
                state.set_visible(True)
                self.show()
                self._game_timer.start(700)

    def _stop_game(self):
        self._game_active = None
        self._game_step = 0
        self._game_timer.stop()
        state.set_emotion("neutral")
        state.set_visible(True)
        self.show()
        self.setWindowOpacity(1.0)
        logger.info("Game stopped")

    def _game_tick(self):
        if not self._game_active:
            self._game_timer.stop()
            return
        game = next((g for g in GAMES if g["id"] == self._game_active), None)
        if not game:
            return
        self._game_step += 1
        if self._game_active == "dance":
            motions = ["Tap@Body", "Flick@Body", "Tap", "Flick", "FlickDown"]
            emotions = ["joy", "amusement", "love"]
            state.play_motion(random.choice(motions), 0, 2)
            state.set_emotion(random.choice(emotions))
            if self._game_step >= 8:
                self._game_speak("Фух, натанцевалась! Классно потанцевали!")
                self._stop_game()
        elif self._game_active == "pansu_click":
            self._game_step -= 1
            self._pc_tick()
        elif self._game_active == "live":
            pass

    def _pc_tick(self):
        import random as rnd
        step = self._game_step
        if step == 0:
            self._pc_countdown += 1
            if self._pc_countdown >= 3:
                screen = QGuiApplication.primaryScreen().availableGeometry()
                cx = (screen.width() - self.width()) // 2
                cy = (screen.height() - self.height()) // 2
                self.move(cx, cy)
                state.set_visible(True)
                self.show()
                state.set_emotion("love")
                self._game_timer.stop()
                self._pc_countdown = 0
                self._game_step = 1
                state.set_mouth_open(0.0)
                self._game_speak("Рассказать правила? Одиночный клик. Или сразу играем? Двойной.")
        elif step == 2:
            self._pc_countdown += 1
            if self._pc_countdown == 1:
                self.move(self._pc_center_x, -self.height())
            elif self._pc_countdown == 2:
                self.move(self._pc_center_x, self._pc_center_y)
                state.set_emotion("love")
                self._game_speak("Раз!")
            elif self._pc_countdown == 3:
                self.move(self._pc_center_x, -self.height())
            elif self._pc_countdown == 4:
                self.move(self._pc_center_x, self._pc_center_y)
                state.set_emotion("love")
                self._game_speak("Два!")
            elif self._pc_countdown == 5:
                self.move(self._pc_center_x, -self.height())
            elif self._pc_countdown == 6:
                self.move(self._pc_center_x, self._pc_center_y)
                state.set_emotion("love")
                self._game_speak("Три!")
            elif self._pc_countdown == 7:
                self.move(self._pc_center_x, -self.height())
            elif self._pc_countdown == 8:
                self.move(self._pc_center_x, self._pc_center_y)
                state.set_emotion("love")
            elif self._pc_countdown == 9:
                self._game_speak("Жми!")
            elif self._pc_countdown == 10:
                pass
            elif self._pc_countdown == 11:
                state.set_mouth_open(0.0)
                state.set_emotion("love")
                self._game_step = 3
                self._pc_countdown = 0
                self._game_timer.stop()
        elif step == 4:
            self._pc_countdown += 1
            if self._pc_countdown >= 3:
                state.set_visible(False)
                self.hide()
                self._game_step = 5
                self._pc_countdown = 0
                self._pc_round = 0
                self._pc_pansu_count = 0
                self._pc_shots = []
        elif step == 5:
            self._pc_countdown += 1
            if self._pc_countdown >= 3:
                screen = QGuiApplication.primaryScreen().availableGeometry()
                sx, sy = screen.width(), screen.height()
                wx, wy = self.width(), self.height()
                tx = rnd.randint(0, max(0, sx - wx))
                ty = rnd.randint(0, max(0, sy - wy))
                self.move(tx, ty)
                state.set_mouth_open(0.0)
                pansu_types = ["pansu_shot2", "pansu_shot3"]
                if self._pc_round == 9 and self._pc_pansu_count == 0:
                    emotion = rnd.choice(pansu_types)
                else:
                    emotion = rnd.choice(["love", "eyes_closed"] + pansu_types)
                state.set_emotion(emotion)
                if emotion in pansu_types:
                    self._pc_pansu_count += 1
                self._pc_shots.append(emotion)
                state.set_visible(True)
                self.show()
                self._pc_round += 1
                self._pc_countdown = 0
                if self._pc_round >= 10:
                    self._game_step = 6
                    self._pc_countdown = 0
        elif step == 6:
            self._pc_countdown += 1
            if self._pc_countdown >= 3:
                self._game_step = 7
                self._pc_countdown = 0
                self._game_timer.stop()
                screen = QGuiApplication.primaryScreen().availableGeometry()
                cx = (screen.width() - self.width()) // 2
                cy = (screen.height() - self.height()) // 2
                self.move(cx, cy)
                state.set_emotion("love")
                self._game_speak("Сколько раз увидел мои трусики?")
        elif step == 8:
            self._pc_countdown += 1
            if self._pc_countdown == 2:
                state.set_emotion("no_panty")
            elif self._pc_countdown >= 5:
                self._game_step = 10
                self._pc_countdown = 0
                state.set_emotion("love")
        elif step == 9:
            self._pc_countdown += 1
            if self._pc_countdown >= 5:
                self._game_step = 1
                self._pc_countdown = 0
                self._pc_rules_spoken = False
                self._game_timer.stop()
                screen = QGuiApplication.primaryScreen().availableGeometry()
                cx = (screen.width() - self.width()) // 2
                cy = (screen.height() - self.height()) // 2
                self.move(cx, cy)
                state.set_emotion("love")
        elif step == 10:
            self._pc_countdown += 1
            if self._pc_countdown == 1:
                state.set_emotion("love")
            elif self._pc_countdown >= 5:
                self._stop_game()

    def _pc_check_answer(self):
        if self._game_active != "pansu_click":
            return
        self._game_timer.stop()
        self._pc_confirm_timer.stop()
        if self._pc_answer == self._pc_pansu_count:
            self._game_step = 8
            self._pc_countdown = 0
            state.set_emotion("love")
            self._game_speak("А ты внимательный!")
            self._game_timer.start(1000)
        else:
            self._game_step = 9
            self._pc_countdown = 0
            state.set_emotion("love")
            self._game_speak("Неправильно! Попробуй снова!")
            self._game_timer.start(1000)

    def _react_click_game(self):
        if self._game_active == "pansu_click":
            if self._game_step == 1:
                if self._pc_rules_spoken:
                    return
                state.set_mouth_open(0.0)
                state.set_emotion("love")
                rules = ("Кликни столько раз, сколько увидишь мои трусики! Двойной клик для старта!")
                self._game_speak(rules)
                self._pc_rules_spoken = True
            elif self._game_step == 3:
                self._game_step = 4
                self._pc_countdown = 0
                state.set_mouth_open(0.0)
                state.set_emotion("love")
                state.set_visible(False)
                self.hide()
                self._game_timer.start(1000)
            elif self._game_step == 7:
                self._pc_answer += 1
                self._pc_confirm_timer.stop()
                self._pc_confirm_timer.start(2000)
            elif self._game_step == 8:
                pass
        elif self._game_active == "hide_seek":
            screen = QGuiApplication.primaryScreen().availableGeometry()
            tx = random.randint(50, screen.width() - self.width() - 50)
            ty = random.randint(50, screen.height() - self.height() - 100)
            self.move(tx, ty)
            self._game_speak("Не поймала! Ещё раз!")
            state.play_motion("Flick", 0, 2)
            self._game_step += 1
            if self._game_step >= 5:
                self._game_speak("Ой, устала! Давай в другой раз")
                self._stop_game()
        elif self._game_active == "tag":
            state.set_emotion("surprise")
            state.play_motion("Tap", 0, 2)
            self._game_speak("Щёлк!")
            self._game_step += 1
            if self._game_step >= 5:
                self._game_speak("Ой! Вся изщёлкалась!")
                self._stop_game()
        elif self._game_active == "compliment":
            compliments = [
                "Ты самый лучший!", "У тебя отличная улыбка!",
                "Ты очень умный!", "С тобой так весело!",
                "Ты классно выглядишь!", "Ты мой герой!",
            ]
            self._game_speak(random.choice(compliments))
            state.set_emotion("love")
            state.play_motion("Tap", 0, 2)
            self._game_step += 1
            if self._game_step >= 3:
                self._stop_game()
        elif self._game_active == "emotion_game":
            emotions = ["joy", "surprise", "anger", "sadness", "love"]
            emoji = {"joy": "😊", "surprise": "😮", "anger": "😠", "sadness": "😢", "love": "😍"}
            current = random.choice(emotions)
            state.set_emotion(current)
            self._game_speak(f"Угадай! {emoji.get(current, '🤔')}")
            self._game_step += 1
            if self._game_step >= 5:
                self._game_speak("Отлично поиграли! Ты хорошо знаешь эмоции!")
                self._stop_game()
        elif self._game_active == "mimic":
            emotions = ["joy", "surprise", "anger", "love", "amusement"]
            motions = ["Tap", "Flick", "FlickDown", "Tap@Body"]
            state.set_emotion(random.choice(emotions))
            state.play_motion(random.choice(motions), 0, 2)
            screen = QGuiApplication.primaryScreen().availableGeometry()
            tx = random.randint(50, screen.width() - self.width() - 50)
            ty = random.randint(50, screen.height() - self.height() - 100)
            self.move(tx, ty)
            self._game_step += 1
            if self._game_step >= 5:
                self._game_speak("Супер! Ты всё повторяешь!")
                self._stop_game()

    def _speak_random_click(self):
        import alarm_timer
        if not alarm_timer.get_settings().get("random_clicks_enabled", False):
            return
        import phrases
        import random
        pool = phrases.get("click_random_phrases")
        if isinstance(pool, list) and pool:
            text = random.choice(pool)
            from tts import speak as tts_speak
            tts_speak(text)

    def _speak_click_rc(self):
        import random
        import phrases
        from tts import speak as tts_speak
        if state.get_render_mode() == "sprite":
            pool = [
                "Можешь меня изнасиловать",
                "Я только за!",
                "Можешь когда хочешь",
                "Тебя на долго хватит?",
            ]
            text = random.choice(pool)
        else:
            text = phrases.get("click_rc")
            if not text:
                return
        self._rc_block = True
        tts_speak(text)

    def contextMenuEvent(self, event):
        import tts
        if self._rc_escape_active:
            return
        if self._rc_block and tts.is_speaking():
            self._start_rc_escape()
            return
        self._speak_click_rc()
        try:
            menu = QtWidgets.QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: rgba(28, 28, 30, 240);
                    border: 1px solid rgba(255, 255, 255, 30);
                    border-radius: 12px;
                    padding: 5px;
                    color: #E0E0E0;
                    font-size: 14px;
                }
                QMenu::item {
                    padding: 8px 24px;
                    border-radius: 8px;
                    margin: 2px 4px;
                }
                QMenu::item:selected {
                    background-color: rgba(255, 255, 255, 25);
                    color: #FFFFFF;
                }
                QMenu::separator {
                    height: 1px;
                    background: rgba(255, 255, 255, 30);
                    margin: 4px 8px;
                }
            """)

            action_play = menu.addAction("▶ Play")
            action_play.setCheckable(True)
            action_play.setChecked(self._play_active)

            is_sprite = state.get_render_mode() == "sprite"
            all_modes = play_modes.list_modes()
            filtered = [(pi, m) for pi, m in enumerate(all_modes) if not m.get("requires_sprite") or is_sprite]
            menu_play_mode = menu.addMenu("Play-Options")
            play_items = []
            for pi, m in filtered:
                pa = menu_play_mode.addAction(m["name"])
                pa.setCheckable(True)
                pa.setChecked(pi == self._play_pattern and self._play_active)
                pa.setData("pattern:" + str(pi))
                play_items.append(pa)

            action_live = menu.addAction("🎲 Live")
            action_live.setCheckable(True)
            action_live.setChecked(self._live_active)

            menu_games = menu.addMenu("🎮 Games")
            game_items = []
            for g in GAMES:
                if g.get("requires_sprite") and not is_sprite:
                    continue
                gi = menu_games.addAction(g["icon"] + " " + g["name"])
                gi.setData(g["id"])
                game_items.append(gi)
            if self._game_active:
                gi_stop = menu_games.addAction("⏹ Stop Game")
                gi_stop.setData("_stop")
                game_items.append(gi_stop)

            action_stop_at = None
            if self._at_firing:
                action_stop_at = menu.addAction(f"⏹ Stop {'Alarm' if self._at_data.get('type')=='alarm' else 'Timer'}")

            menu_music = menu.addMenu("🎵 Music")
            music_items = []
            try:
                import music_player
                tracks = music_player.list_tracks()
                if tracks:
                    for t in tracks:
                        mi = menu_music.addAction(t)
                        mi.setCheckable(True)
                        mi.setChecked(t in self._favorite_tracks)
                        mi.setData("fav:" + t)
                        music_items.append(mi)
                    menu_music.addSeparator()
                mi_stop = menu_music.addAction("⏹ Stop")
                mi_stop.setData("music_stop")
                music_items.append(mi_stop)
                mi_next = menu_music.addAction("⏭ Next")
                mi_next.setData("music_next")
                music_items.append(mi_next)
                mi_prev = menu_music.addAction("⏮ Prev")
                mi_prev.setData("music_prev")
                music_items.append(mi_prev)
                mi_random = menu_music.addAction("🎲 Random")
                mi_random.setData("music_random")
                music_items.append(mi_random)
                menu_music.addSeparator()
                loop_state = "✅" if music_player.get_loop() else "🔁"
                mi_loop = menu_music.addAction(f"{loop_state} Loop")
                mi_loop.setData("music_loop")
                music_items.append(mi_loop)
                auto_state = "✅" if music_player.get_autoplay() else "▶▶"
                mi_auto = menu_music.addAction(f"{auto_state} Autoplay")
                mi_auto.setData("music_autoplay")
                music_items.append(mi_auto)
            except Exception:
                mi = menu_music.addAction("(no tracks)")
                mi.setEnabled(False)

            menu.addSeparator()
            music_mode_state = "✅" if self._music_mode_active else "❌"
            action_music_mode = menu.addAction(f"🎵 Music {music_mode_state}")
            action_music_mode.setCheckable(True)
            action_music_mode.setChecked(self._music_mode_active)

            import alarm_timer
            at_cfg = alarm_timer.get_settings()
            alarm_en = at_cfg.get("alarm_enabled", False)
            timer_en = at_cfg.get("timer_enabled", False)
            action_alarm_toggle = menu.addAction(f"🔔 Alarm {'✅' if alarm_en else '❌'}")
            action_alarm_toggle.setCheckable(True)
            action_alarm_toggle.setChecked(alarm_en)
            action_alarm_toggle.setData("alarm_toggle")
            action_timer_toggle = menu.addAction(f"⏲ Timer {'✅' if timer_en else '❌'}")
            action_timer_toggle.setCheckable(True)
            action_timer_toggle.setChecked(timer_en)
            action_timer_toggle.setData("timer_toggle")
            action_say_time = menu.addAction("🕐 Say Time")
            random_clicks_en = at_cfg.get("random_clicks_enabled", False)
            action_random_clicks = menu.addAction(f"🎲 Random Clicks {'✅' if random_clicks_en else '❌'}")
            action_random_clicks.setCheckable(True)
            action_random_clicks.setChecked(random_clicks_en)
            action_random_clicks.setData("random_clicks")
            action_screenshot = menu.addAction("📸 Screenshot")
            import stt
            mic_en = stt.is_listening()
            action_mic = menu.addAction(f"🎤 Mic {'✅' if mic_en else '❌'}")
            action_mic.setCheckable(True)
            action_mic.setChecked(mic_en)
            action_mic.setData("mic_toggle")

            menu.addSeparator()
            model_menu = menu.addMenu("🔄 Switch Model")
            model_items = []
            current_model = state.get_model_name()
            for mk, mv in MODELS.items():
                ma = model_menu.addAction(f"{'✅ ' if mk == current_model else '   '}{mv['label']}")
                ma.setCheckable(True)
                ma.setChecked(mk == current_model)
                ma.setData("model:" + mk)
                model_items.append(ma)

            menu.addSeparator()
            if state.get_render_mode() == "sprite":
                pansu_menu = menu.addMenu("👙 Пансу")
                pansu_items = []
                for pk in ['pansu_shot2', 'pansu_shot3', 'no_panty']:
                    if pk in self._sprite_frames:
                        labels = {'pansu_shot2': 'Шот 2 📸', 'pansu_shot3': 'Шот 3 📸', 'no_panty': 'Без трусов 🚫'}
                        pa = pansu_menu.addAction(labels.get(pk, pk))
                        pa.setData("pansu:" + pk)
                        pansu_items.append(pa)
            else:
                pansu_items = []

            action_web = menu.addAction("🌐 Web Admin")
            action_center = menu.addAction("🖥 Center on Screen")
            action_close = menu.addAction("🙈 Hide")
            action_exit = menu.addAction("✕ Exit")

            menu.addSeparator()
            mcp_menu = menu.addMenu("🤖 MCP Controls")
            music_mcp_en = at_cfg.get("music_mcp_enabled", False)
            action_mcp_music = mcp_menu.addAction(f"Music MCP {'✅' if music_mcp_en else '❌'}")
            action_mcp_music.setCheckable(True)
            action_mcp_music.setChecked(music_mcp_en)
            action_mcp_music.setData("mcp_music")
            ss_mcp_en = at_cfg.get("screenshot_mcp_enabled", False)
            action_mcp_ss = mcp_menu.addAction(f"Screenshot MCP {'✅' if ss_mcp_en else '❌'}")
            action_mcp_ss.setCheckable(True)
            action_mcp_ss.setChecked(ss_mcp_en)
            action_mcp_ss.setData("mcp_ss")
            hide_mcp_en = at_cfg.get("hide_mcp_enabled", True)
            action_mcp_hide = mcp_menu.addAction(f"Hide MCP {'✅' if hide_mcp_en else '❌'}")
            action_mcp_hide.setCheckable(True)
            action_mcp_hide.setChecked(hide_mcp_en)
            action_mcp_hide.setData("mcp_hide")
            control_mcp_en = at_cfg.get("control_mcp_enabled", True)
            action_mcp_control = mcp_menu.addAction(f"Управление MCP {'✅' if control_mcp_en else '❌'}")
            action_mcp_control.setCheckable(True)
            action_mcp_control.setChecked(control_mcp_en)
            action_mcp_control.setData("mcp_control")
            emotion_mcp_en = at_cfg.get("emotion_mcp_enabled", True)
            action_mcp_emotion = mcp_menu.addAction(f"Эмоции MCP {'✅' if emotion_mcp_en else '❌'}")
            action_mcp_emotion.setCheckable(True)
            action_mcp_emotion.setChecked(emotion_mcp_en)
            action_mcp_emotion.setData("mcp_emotion")
            mcp_alarm_en = at_cfg.get("alarm_mcp_enabled", False)
            action_mcp_alarm = mcp_menu.addAction(f"Alarm MCP {'✅' if mcp_alarm_en else '❌'}")
            action_mcp_alarm.setCheckable(True)
            action_mcp_alarm.setChecked(mcp_alarm_en)
            action_mcp_alarm.setData("mcp_alarm")
            mcp_timer_en = at_cfg.get("timer_mcp_enabled", False)
            action_mcp_timer = mcp_menu.addAction(f"Timer MCP {'✅' if mcp_timer_en else '❌'}")
            action_mcp_timer.setCheckable(True)
            action_mcp_timer.setChecked(mcp_timer_en)
            action_mcp_timer.setData("mcp_timer")

            action = menu.exec(event.globalPos())
            if action == action_play:
                if self._play_active:
                    self._stop_play()
                else:
                    self._start_play(self._play_pattern)
            elif action in play_items:
                pi = int(action.data()[8:])
                self._play_pattern = pi
                if not self._play_active:
                    self._start_play(pi)
            elif action == action_live:
                if self._live_active:
                    self._stop_live()
                else:
                    self._start_live()
            elif action in game_items:
                gid = action.data()
                if gid == "_stop":
                    self._stop_game()
                else:
                    self._start_game(gid)
            elif action in music_items:
                cmd = action.data()
                try:
                    import music_player
                    if cmd == "music_stop":
                        music_player.stop()
                    elif cmd == "music_next":
                        music_player.play_next()
                    elif cmd == "music_prev":
                        music_player.play_prev()
                    elif cmd == "music_random":
                        music_player.play_random()
                    elif cmd == "music_loop":
                        music_player.set_loop(not music_player.get_loop())
                    elif cmd == "music_autoplay":
                        music_player.set_autoplay(not music_player.get_autoplay())
                    elif cmd.startswith("play:"):
                        music_player.play_track(cmd[5:])
                    elif cmd.startswith("fav:"):
                        t = cmd[4:]
                        if t in self._favorite_tracks:
                            self._favorite_tracks.discard(t)
                        else:
                            self._favorite_tracks.add(t)
                        self._save_favorite_tracks()
                except Exception as e:
                    logger.debug(f"Music error: {e}")
            elif action == action_music_mode:
                if self._music_mode_active:
                    self._stop_music_mode()
                else:
                    self._start_music_mode()
            elif action == action_stop_at:
                self._stop_alarm_timer_mode()
            elif action == action_say_time:
                now = time.localtime()
                import phrases
                phrases.speak("say_time", hour=now.tm_hour, minute=now.tm_min)
            elif action == action_alarm_toggle:
                import alarm_timer
                en = not at_cfg.get("alarm_enabled", False)
                alarm_timer.save_settings({"alarm_enabled": en})
            elif action == action_timer_toggle:
                import alarm_timer
                en = not at_cfg.get("timer_enabled", False)
                alarm_timer.save_settings({"timer_enabled": en})
            elif action.data() == "random_clicks":
                import alarm_timer
                s = alarm_timer.get_settings()
                alarm_timer.save_settings({"random_clicks_enabled": not s.get("random_clicks_enabled", False)})
            elif action.data() == "mic_toggle":
                import stt
                try:
                    if stt.is_listening():
                        stt.stop_listening()
                    else:
                        stt.start_listening()
                except Exception as e:
                    logger.error(f"Mic toggle failed: {e}")
            elif action.data() == "mcp_music":
                import alarm_timer
                s = alarm_timer.get_settings()
                v = not s.get("music_mcp_enabled", False)
                alarm_timer.save_settings({"music_mcp_enabled": v})
                action.setText(f"Music MCP {'✅' if v else '❌'}")
            elif action.data() == "mcp_ss":
                import alarm_timer
                s = alarm_timer.get_settings()
                v = not s.get("screenshot_mcp_enabled", False)
                alarm_timer.save_settings({"screenshot_mcp_enabled": v})
                action.setText(f"Screenshot MCP {'✅' if v else '❌'}")
            elif action.data() == "mcp_hide":
                import alarm_timer
                s = alarm_timer.get_settings()
                v = not s.get("hide_mcp_enabled", True)
                alarm_timer.save_settings({"hide_mcp_enabled": v})
                action.setText(f"Hide MCP {'✅' if v else '❌'}")
            elif action.data() == "mcp_control":
                import alarm_timer
                s = alarm_timer.get_settings()
                v = not s.get("control_mcp_enabled", True)
                alarm_timer.save_settings({"control_mcp_enabled": v})
                action.setText(f"Управление MCP {'✅' if v else '❌'}")
            elif action.data() == "mcp_emotion":
                import alarm_timer
                s = alarm_timer.get_settings()
                alarm_timer.save_settings({"emotion_mcp_enabled": not s.get("emotion_mcp_enabled", True)})
            elif action.data() == "mcp_alarm":
                import alarm_timer
                s = alarm_timer.get_settings()
                alarm_timer.save_settings({"alarm_mcp_enabled": not s.get("alarm_mcp_enabled", False)})
            elif action.data() == "mcp_timer":
                import alarm_timer
                s = alarm_timer.get_settings()
                alarm_timer.save_settings({"timer_mcp_enabled": not s.get("timer_mcp_enabled", False)})
            elif action in model_items:
                model_name = action.data()[6:]
                result = self.switch_model(model_name)
                logger.info(f"Model switch: {result}")
            elif pansu_items and action in pansu_items:
                pk = action.data()[6:]
                state.set_emotion(pk)
                logger.info(f"Pansu shot: {pk}")
            elif action == action_web:
                import webbrowser
                webbrowser.open("http://127.0.0.1:8766")
            elif action == action_screenshot:
                self._take_screenshot_action()
            elif action == action_center:
                screen = QGuiApplication.primaryScreen().geometry()
                self.move(screen.width() // 2 - self.width() // 2,
                          screen.height() // 2 - self.height() // 2)
                import phrases
                phrases.speak("center_on_screen")
            elif action == action_close:
                self._start_hide_animation()
            elif action == action_exit:
                self._start_exit_animation()
        except Exception as e:
            logger.debug(f"contextMenu error: {e}")

    def _start_play(self, pattern=None):
        if self._live_active:
            self._stop_live()
        self._play_active = True
        if pattern is not None:
            self._play_pattern = pattern
        else:
            is_sprite = state.get_render_mode() == "sprite"
            mode = play_modes.random_mode(sprite_only=is_sprite)
            self._play_pattern = play_modes.index_of(mode["name"])
        mode = play_modes.get_mode(self._play_pattern)
        if mode and mode.get("requires_sprite") and state.get_render_mode() != "sprite":
            self._play_active = False
            logger.info(f"Mode '{mode['name']}' requires sprite mode")
            return
        ctx = play_modes.ModeContext(self, state)
        self._mode_ctx = ctx
        try:
            mode["module"].start(ctx)
        except Exception as e:
            logger.debug(f"Play mode start error: {e}")
        interval = ctx.data.get("interval", mode["interval"])
        self._play_timer.start(interval)
        logger.info(f"Play mode started ({mode['name']})")

    def _stop_play(self):
        self._play_active = False
        self._play_timer.stop()
        if self._mode_ctx:
            mode = play_modes.get_mode(self._play_pattern)
            if mode:
                try:
                    mode["module"].stop(self._mode_ctx)
                except Exception as e:
                    logger.debug(f"Play mode stop error: {e}")
        self._mode_ctx = None
        state.set_emotion("neutral")
        state.set_param("ParamBodyAngleZ", 0)
        state.set_visible(True)
        self.show()
        self.setWindowOpacity(1.0)
        logger.info("Play mode stopped")

    def _play_tick(self):
        if not self._play_active or not self._mode_ctx:
            return
        if state.get_render_mode() == "live2d" and not self.live2d_model:
            return
        mode = play_modes.get_mode(self._play_pattern)
        if not mode:
            return
        try:
            mode["module"].tick(self._mode_ctx)
        except Exception as e:
            logger.debug(f"Play mode tick error: {e}")
        # update timer interval if mode changed it
        new_interval = self._mode_ctx.data.get("interval")
        if new_interval and new_interval != self._play_timer.interval():
            self._play_timer.setInterval(new_interval)

    def _check_alarm_timer(self):
        import alarm_timer
        try:
            self._check_missed_alarm()
            if not self._alarm_triggered and alarm_timer.check_alarm():
                self._alarm_triggered = True
                data = alarm_timer.fire_alarm()
                self._start_alarm_timer_mode(data)
            if not self._timer_triggered and alarm_timer.check_timer():
                self._timer_triggered = True
                data = alarm_timer.fire_timer()
                self._start_alarm_timer_mode(data)
            if not self._mcp_alarm_triggered and alarm_timer.check_mcp_alarm():
                self._mcp_alarm_triggered = True
                data = alarm_timer.fire_mcp_alarm()
                self._start_alarm_timer_mode(data)
            if not self._mcp_timer_triggered and alarm_timer.check_mcp_timer():
                self._mcp_timer_triggered = True
                data = alarm_timer.fire_mcp_timer()
                self._start_alarm_timer_mode(data)
        except Exception as e:
            logger.debug(f"Alarm/timer check error: {e}")

    def _check_missed_alarm(self):
        if self._at_firing:
            return
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if getattr(self, '_missed_alarm_checked', None) == today:
            return
        self._missed_alarm_checked = today
        import alarm_timer
        cfg = alarm_timer.get_settings()
        if not cfg.get("alarm_enabled", False):
            return
        alarm_time = cfg.get("alarm_time", "08:00")
        now_minutes = now.hour * 60 + now.minute
        try:
            parts = alarm_time.split(":")
            alarm_minutes = int(parts[0]) * 60 + int(parts[1])
        except Exception:
            return
        if now_minutes > alarm_minutes + 2:
            self._missed_alarm_text = cfg.get("alarm_text", "Будильник пропущен!")
            self._missed_alarm_pending = True

    def _start_alarm_timer_mode(self, data):
        if self._at_firing:
            return
        self._at_data = data
        self._at_repeat_count = 0
        self._at_firing = True
        self._at_counter = 0
        self._at_timer = QtCore.QTimer()
        self._at_timer.timeout.connect(self._at_tick)
        self._at_timer.start(1000)
        self._at_speak()
        logger.info(f"Alarm/timer mode started: {data.get('type')} - {data.get('text')}")

    def _at_speak(self):
        import tts
        text = self._at_data.get("text", "")
        if text:
            try:
                tts.speak(text)
            except Exception:
                pass
        song = self._at_data.get("song", "")
        if song:
            try:
                import music_player
                music_player.play_track(song)
            except Exception:
                pass

    def _at_tick(self):
        if not self._at_firing or not self.live2d_model:
            return
        self._at_counter += 1
        emotions = ["joy", "surprise", "amusement", "love"]
        state.set_emotion(random.choice(emotions))
        state.play_motion(random.choice(["Tap", "Flick", "FlickDown", "Tap@Body"]), 0, 2)
        tilt = math.sin(self._at_counter * 0.2) * 10
        state.set_param("ParamBodyAngleZ", tilt)
        self.setWindowOpacity(0.8 + 0.2 * math.sin(self._at_counter * 0.5))
        if self._at_counter % 5 == 0:
            state.set_emotion(random.choice(emotions))
        replay = self._at_data.get("replay_interval", 0)
        if replay > 0 and self._at_counter % replay == 0:
            self._at_speak()
        stop_after = self._at_data.get("stop_after", 0)
        if stop_after > 0 and self._at_counter >= stop_after:
            self._stop_alarm_timer_mode()

    def _on_alarm_timer_cfg_change(self, cfg):
        """Called from alarm_timer.save_settings (may be any thread)."""
        import copy
        self._pending_cfg = copy.deepcopy(cfg)
        self._at_cfg_signal.start(0)

    def _on_at_cfg_queue(self):
        cfg = getattr(self, '_pending_cfg', None)
        if cfg is None:
            return
        self._pending_cfg = None
        prev = getattr(self, '_prev_at_cfg', {})
        if cfg.get("alarm_enabled", False) and not prev.get("alarm_enabled", False):
            alarm_time = cfg.get("alarm_time", "08:00")
            import phrases
            phrases.speak("alarm_set_ui", time=alarm_time)
        if cfg.get("timer_enabled", False) and not prev.get("timer_enabled", False):
            duration_sec = cfg.get("timer_duration", 300)
            mins = duration_sec // 60
            sec_rem = duration_sec % 60
            import phrases
            if mins >= 1:
                if sec_rem:
                    phrases.speak("timer_set_ui_mins_secs", mins=mins, secs=sec_rem)
                else:
                    phrases.speak("timer_set_ui_mins", mins=mins)
            else:
                phrases.speak("timer_set_ui_secs", secs=sec_rem)
        self._prev_at_cfg = cfg
        if self._at_firing and self._at_data:
            at_type = self._at_data.get("type", "alarm")
            alarm_on = cfg.get("alarm_enabled", False) if at_type == "alarm" else cfg.get("timer_enabled", False)
            if not alarm_on:
                self._stop_alarm_timer_mode()

    def _stop_alarm_timer_mode(self):
        if hasattr(self, '_at_timer') and self._at_timer:
            self._at_timer.stop()
        self._at_firing = False
        self._alarm_triggered = False
        self._timer_triggered = False
        self._mcp_alarm_triggered = False
        self._mcp_timer_triggered = False
        self.setWindowOpacity(1.0)
        state.set_emotion("neutral")
        state.set_param("ParamBodyAngleZ", 0)
        logger.info("Alarm/timer mode stopped")

    def _at_click(self):
        if not self._at_data:
            return
        import alarm_timer
        cfg = alarm_timer.get_settings()
        auto = cfg.get("alarm_auto_repeat" if self._at_data.get("type") == "alarm" else "timer_auto_repeat", False)
        if auto:
            self._at_repeat_count += 1
            max_repeat = self._at_data.get("repeat", 1)
            if max_repeat <= 0 or self._at_repeat_count < max_repeat:
                self._at_speak()
            else:
                self._stop_alarm_timer_mode()

    def _start_live(self):
        self._live_active = True
        interval = self._get_live_interval()
        self._live_timer.start(interval * 1000)
        self._live_tick()
        logger.info(f"Live mode started (interval={interval}s)")

    def _get_live_interval(self):
        try:
            with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return int(cfg.get("live_interval", 30))
        except Exception:
            return 30

    def _get_live_phrases(self):
        try:
            with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
                cfg = json.load(f)
            phrases = cfg.get("live_phrases", [])
            if isinstance(phrases, str):
                phrases = [p.strip() for p in phrases.split("\n") if p.strip()]
            return phrases
        except Exception:
            return []

    def _stop_live(self):
        self._live_active = False
        self._live_timer.stop()
        if self._game_active:
            self._stop_game()
        logger.info("Live mode stopped")

    def _start_music_mode(self):
        self._music_mode_active = True
        try:
            import music_player
            tracks = music_player.list_tracks()
            if self._favorite_tracks:
                candidates = [t for t in tracks if t in self._favorite_tracks]
                if candidates:
                    music_player.play_track(random.choice(candidates))
                    return
            if tracks:
                music_player.play_track(random.choice(tracks))
        except Exception:
            pass

    def _stop_music_mode(self):
        self._music_mode_active = False
        try:
            import music_player
            music_player.stop()
        except Exception:
            pass

    def _save_favorite_tracks(self):
        try:
            cfg = {}
            cf = os.path.join(BASE_DIR, "config.json")
            if os.path.exists(cf):
                with open(cf, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["favorite_tracks"] = list(self._favorite_tracks)
            with open(cf, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    SCREENSHOT_PATH = os.path.join(BASE_DIR, "_screenshot.png")
    SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")

    def take_screenshot_threadsafe(self, delay_ms=0):
        """Request screenshot from any thread. Blocks until done. Returns base64 or None."""
        self._screenshot_event.clear()
        self._screenshot_result = None
        self._screenshot_delay = delay_ms
        QtCore.QMetaObject.invokeMethod(
            self, "_do_queued_screenshot",
            QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._screenshot_event.wait(timeout=10)
        return self._screenshot_result

    @QtCore.pyqtSlot()
    def _do_queued_screenshot(self):
        """Runs in Qt main thread via invokeMethod."""
        delay = self._screenshot_delay
        if delay > 0:
            QtCore.QTimer.singleShot(delay, self._capture_screen)
        else:
            self._capture_screen()

    def _capture_screen(self):
        try:
            screen = QGuiApplication.primaryScreen()
            if screen is None:
                logger.error("Screenshot error: no primary screen")
                self._screenshot_result = None
                self._on_screenshot_ended("err")
                return
            pixmap = screen.grabWindow(0)
            if pixmap is None or pixmap.isNull():
                logger.error("Screenshot error: grabWindow returned null, fallback to widget grab")
                pixmap = self.grab()
                if pixmap is None or pixmap.isNull():
                    self._screenshot_result = None
                    self._on_screenshot_ended("err")
                    return
            ok = pixmap.save(self.SCREENSHOT_PATH, "PNG")
            if not ok:
                logger.error("Screenshot error: save failed")
                self._screenshot_result = None
                self._on_screenshot_ended("err")
                return
            try:
                os.makedirs(self.SCREENSHOT_DIR, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_path = os.path.join(self.SCREENSHOT_DIR, f"screenshot_{ts}.png")
                pixmap.save(archive_path, "PNG")
            except Exception as e:
                logger.warning(f"Screenshot archive save failed: {e}")
            with open(self.SCREENSHOT_PATH, "rb") as f:
                self._screenshot_result = base64.b64encode(f.read()).decode("utf-8")
            self._on_screenshot_ended("ok")
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            self._screenshot_result = None
            self._on_screenshot_ended("err")

    def _rapid_emotion_tick(self):
        emotions = ["joy", "surprise", "love", "amusement", "fear", "sad"]
        motions = ["Tap", "Flick", "FlickDown", "Tap@Body"]
        state.set_emotion(random.choice(emotions))
        state.play_motion(random.choice(motions), 0, 2)
        tilt = random.uniform(-15, 15)
        state.set_param("ParamBodyAngleZ", tilt)

    def _start_climax(self):
        import alarm_timer
        cfg = alarm_timer.get_settings()
        if not cfg.get("climax_enabled", True):
            return
        duration = cfg.get("climax_duration", 20)
        self._climax_active = True
        self._climax_end = time.time() + duration
        self._climax_block_clicks = cfg.get("climax_block_clicks", False)
        self._climax_emotions = cfg.get("climax_emotions",
            ["joy", "surprise", "love", "amusement", "fear", "sad", "anger"])
        self._climax_motions = cfg.get("climax_motions",
            ["Tap", "Flick", "FlickDown", "Tap@Body"])
        self._climax_timer = QtCore.QTimer()
        self._climax_timer.timeout.connect(self._climax_tick)
        self._climax_timer.start(250)
        state.set_emotion("love")
        state.play_motion("Tap", 0, 2)

    def _climax_tick(self):
        if not self._climax_active or not self._climax_timer:
            return
        if time.time() >= self._climax_end:
            self._climax_active = False
            self._climax_timer.stop()
            state.set_emotion("neutral")
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 100)
            self.setWindowOpacity(1.0)
            return
        state.set_emotion(random.choice(self._climax_emotions))
        state.play_motion(random.choice(self._climax_motions), 0, 2)
        state.set_param("ParamBodyAngleZ", random.uniform(-20, 20))
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(
            random.randint(0, screen.width() - self.width()),
            random.randint(0, screen.height() - self.height() - 40)
        )
        flicker = 0.5 + 0.5 * random.random()
        self.setWindowOpacity(flicker)

    def _start_rc_escape(self):
        self._rc_block = False
        self._rc_escape_active = True
        self._rc_escape_phase = 0
        self._rc_escape_counter = 0
        import phrases
        phrases.speak("click_rc_block_phrase")
        self._rc_escape_timer = QtCore.QTimer()
        self._rc_escape_timer.timeout.connect(self._rc_escape_tick)
        self._rc_escape_timer.start(100)

    def _rc_escape_tick(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self._rc_escape_counter += 1

        if self._rc_escape_phase == 0:
            self.setWindowOpacity(1.0)
            state.set_emotion(random.choice(["fear", "surprise", "anger", "sad"]))
            state.play_motion(random.choice(["Tap", "Flick", "FlickDown", "Tap@Body"]), 0, 2)
            state.set_param("ParamBodyAngleZ", random.uniform(-12, 12))
            import tts
            if not tts.is_speaking() and self._rc_escape_counter >= 5:
                self._rc_escape_phase = 1
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 1:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.move(
                random.randint(0, screen.width() - self.width()),
                random.randint(0, screen.height() - self.height() - 40)
            )
            self.setWindowOpacity(0.3 + 0.7 * random.random())
            state.set_emotion(random.choice(["fear", "surprise", "anger", "sad"]))
            state.play_motion(random.choice(["Tap", "Flick", "FlickDown", "Tap@Body"]), 0, 2)
            state.set_param("ParamBodyAngleZ", random.uniform(-20, 20))
            if self._rc_escape_counter >= 15:
                self._rc_escape_phase = 2
                self._rc_escape_counter = 0
                self.setWindowOpacity(1.0)

        elif self._rc_escape_phase == 2:
            target_x = screen.width() - self.width() - 20
            target_y = screen.height() - self.height() - 100
            if self._rc_escape_counter == 0:
                self.move(0, screen.height() - self.height() - 100)
            elif self._rc_escape_counter <= 4:
                progress = self._rc_escape_counter / 4
                x = int(0 + (target_x - 0) * progress)
                y = int((screen.height() - self.height() - 100) * (1 - progress) + target_y * progress)
                self.move(x, y)
            else:
                self.move(target_x, target_y)
                self._rc_escape_phase = 3
                self._rc_escape_counter = 0
                import phrases
                phrases.speak("click_rc_hide_phrase")

        elif self._rc_escape_phase == 3:
            import tts
            if self._rc_escape_counter >= 20 and not tts.is_speaking():
                self._rc_escape_phase = 4
                self._rc_escape_counter = 0
                self.setWindowOpacity(0.0)

        elif self._rc_escape_phase == 4:
            if self._rc_escape_counter >= 3:
                self._rc_escape_phase = 5
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 5:
            self.setWindowOpacity(1.0)
            cy = screen.height() // 2 - self.height() // 2
            start_x = screen.width() + 10
            end_x = screen.width() - 200
            progress = self._rc_escape_counter / 5
            if progress <= 1:
                x = int(start_x + (end_x - start_x) * progress)
                self.move(x, cy)
            else:
                self.move(end_x, cy)
                self._rc_escape_phase = 6
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 6:
            x = screen.width() - 200
            y = screen.height() // 2 - self.height() // 2
            self.move(x, y)
            self.setWindowOpacity(1.0)
            if self._rc_escape_counter >= 20:
                self._rc_escape_phase = 7
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 7:
            cy = screen.height() // 2 - self.height() // 2
            start_x = screen.width() + 10
            end_x = -self.width() - 10
            progress = self._rc_escape_counter / 15
            if progress <= 1:
                x = int(start_x + (end_x - start_x) * progress)
                self.move(x, cy)
            else:
                self.move(end_x, cy)
                self._rc_escape_phase = 8
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 8:
            x = -self.width() + 200
            y = screen.height() // 2 - self.height() // 2
            self.move(x, y)
            if self._rc_escape_counter >= 30:
                self.move(-self.width() - 10, y)
                self._rc_escape_phase = 9
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 9:
            total = 10
            progress = self._rc_escape_counter / total
            if progress <= 1:
                cx = screen.width() // 2 - self.width() // 2
                y = int((screen.height() - self.height()) * progress)
                self.move(cx, y)
                flicker = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(self._rc_escape_counter))
                self.setWindowOpacity(flicker)
            else:
                self.setWindowOpacity(1.0)
                self._rc_escape_phase = 10
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 10:
            cx = screen.width() // 2 - self.width() // 2
            y = screen.height() // 2 - self.height() // 2
            self.move(cx, y)
            blink = self._rc_escape_counter % 5
            self.setWindowOpacity(0.0 if blink >= 3 else 1.0)
            if self._rc_escape_counter >= 15:
                self.setWindowOpacity(1.0)
                self._rc_escape_phase = 11
                self._rc_escape_counter = 0

        elif self._rc_escape_phase == 11:
            if self._rc_escape_counter == 0:
                import phrases
                phrases.speak("click_rc_tray_phrase")
            import tts
            if not tts.is_speaking() and self._rc_escape_counter >= 5:
                self._rc_escape_active = False
                self._rc_escape_timer.stop()
                QtCore.QTimer.singleShot(200, self._finish_rc_escape)

    def _finish_rc_escape(self):
        import tts
        if tts.is_speaking():
            QtCore.QTimer.singleShot(200, self._finish_rc_escape)
            return
        self._start_hide_animation()

    def _take_screenshot_action(self):
        self._screenshot_event.clear()
        self._screenshot_result = None
        self._screenshot_delay = 500
        QtCore.QMetaObject.invokeMethod(
            self, "_do_queued_screenshot",
            QtCore.Qt.ConnectionType.QueuedConnection
        )

    def _on_screenshot_ended(self, status):
        try:
            import phrases
            if status == "ok":
                state.set_emotion("surprise")
                phrases.speak("screenshot_success")
            else:
                state.set_emotion("sad")
                phrases.speak("screenshot_fail")
        except Exception:
            pass
        self._screenshot_event.set()

    def _pick_live_track(self, tracks):
        if not tracks:
            return None
        if self._favorite_tracks:
            candidates = [t for t in tracks if t in self._favorite_tracks]
            if candidates:
                return random.choice(candidates)
        return random.choice(tracks)

    def _live_tick(self):
        if not self._live_active:
            return
        if state.get_render_mode() == "live2d" and not self.live2d_model:
            return
        try:
            live_phrases = self._get_live_phrases()
            if not live_phrases:
                return
            phrase = random.choice(live_phrases)
            try:
                import tts
                tts.speak(phrase)
            except Exception:
                pass
            state.set_emotion("joy")
            if self.live2d_model:
                state.play_motion("Tap", 0, 2)
        except Exception:
            pass

    def closeEvent(self, event):
        logger.info("Live2D window closing...")
        if self._at_firing:
            self._stop_alarm_timer_mode()
        if self._play_active:
            self._stop_play()
        if self._live_active:
            self._stop_live()
        if self._music_mode_active:
            self._stop_music_mode()
        if self.timer_id:
            self.killTimer(self.timer_id)
            self.timer_id = None
        if self.live2d_model:
            try:
                live2d.dispose()
            except Exception:
                pass
            self.live2d_model = None
        self._sprite_frames.clear()
        self._sprite_loaded = False
        super().closeEvent(event)


def start_display(config: dict) -> Live2DDisplayWindow:
    model_rel = config.get("model_path", "")
    model_path = _resolve_path(model_rel)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    widget = Live2DDisplayWindow(model_path, config)
    widget.show()
    return widget

_display_widget = None

def get_widget():
    global _display_widget
    return _display_widget

def set_widget(w):
    global _display_widget
    _display_widget = w
