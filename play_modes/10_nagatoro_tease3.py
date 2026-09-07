import random
import math
import time
from PyQt6.QtGui import QGuiApplication

NAME = "Nagatoro Tease 3"
INTERVAL = 50
CLICK_STOPS = False
ESCAPE_STOPS = True
REQUIRES_SPRITE = True

_PANSU = ["pansu_shot2", "pansu_shot3"]


def _rand_pos(w):
    screen = QGuiApplication.primaryScreen().availableGeometry()
    sx, sy = screen.width(), screen.height()
    wx, wy = w.width(), w.height()
    return random.randint(0, max(0, sx - wx)), random.randint(0, max(0, sy - wy))


def start(ctx):
    ctx.data["phase"] = "intro"
    ctx.data["t"] = 0
    ctx.data["caught_time"] = 0
    ctx.state.set_visible(True)
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)
    ctx.state.set_emotion("love")


def stop(ctx):
    ctx.state.set_visible(True)
    ctx.state.set_emotion("neutral")
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)
    ctx.data["phase"] = "done"


def mouse_down(ctx):
    if ctx.data["phase"] in ("hunt", "intro"):
        ctx.data["phase"] = "caught"
        ctx.data["caught_time"] = time.time()
        ctx.state.set_emotion("love")


def mouse_up(ctx):
    if ctx.data["phase"] == "caught":
        elapsed = time.time() - ctx.data["caught_time"]
        if elapsed < 5.0:
            ctx.data["phase"] = "hunt"
            ctx.data["t"] = 0
            ctx.state.set_emotion("neutral")


def click(ctx):
    pass


def tick(ctx):
    phase = ctx.data["phase"]
    step = ctx.data.get("interval", 50)
    w = ctx.window
    state = ctx.state

    if phase == "intro":
        t = ctx.data["t"] + step
        ctx.data["t"] = t
        if t >= 1000:
            ctx.data["phase"] = "hunt"
            ctx.data["t"] = 0
            ctx.state.set_emotion("neutral")

    elif phase == "hunt":
        t = ctx.data["t"] + step
        ctx.data["t"] = t
        if t >= 2500:
            tx, ty = _rand_pos(w)
            w.move(tx, ty)
            state.set_emotion(random.choice(["love", "amusement", "surprise"]))
            ctx.data["t"] = 0

    elif phase == "caught":
        elapsed = time.time() - ctx.data["caught_time"]
        state.set_emotion("love")
        if elapsed >= 5.0:
            ctx.data["phase"] = "jump"
            ctx.data["t"] = 0
            ctx.data["jump_left"] = 3
            ctx.data["jump_sx"] = w.pos().x()
            ctx.data["jump_sy"] = w.pos().y()
            state.set_emotion("surprise")
            import tts
            tts.speak("Ай! Отпусти!")

    elif phase == "jump":
        t = ctx.data["t"] + step
        ctx.data["t"] = t
        jl = ctx.data["jump_left"]
        sx, sy = ctx.data["jump_sx"], ctx.data["jump_sy"]
        progress = min(t / 400.0, 1.0)
        if jl == 3:
            tx, ty = sx - 150, sy - 100
        elif jl == 2:
            tx, ty = sx + 200, sy + 80
        else:
            tx, ty = sx - 100, sy + 150
        cx = sx + (tx - sx) * progress
        cy = sy + (ty - sy) * progress + abs(math.sin(progress * math.pi * 3)) * 60
        w.move(int(cx), int(cy))
        state.set_emotion("surprise")
        if progress >= 1.0:
            jl -= 1
            if jl > 0:
                ctx.data["jump_left"] = jl
                ctx.data["jump_sx"], ctx.data["jump_sy"] = tx, ty
                ctx.data["t"] = 0
            else:
                ctx.data["phase"] = "home"
                ctx.data["home_sx"] = tx
                ctx.data["home_sy"] = ty
                ctx.data["t"] = 0

    elif phase == "home":
        t = ctx.data["t"] + step
        ctx.data["t"] = t
        progress = min(t / 600.0, 1.0)
        fx, fy = ctx.data["home_sx"], ctx.data["home_sy"]
        screen = QGuiApplication.primaryScreen().availableGeometry()
        tx = (screen.width() - w.width()) // 2
        ty = (screen.height() - w.height()) // 2
        cx = fx + (tx - fx) * progress
        cy = fy + (ty - fy) * progress
        w.move(int(cx), int(cy))
        state.set_emotion("surprise")
        if progress >= 1.0:
            ctx.data["phase"] = "love_show"
            ctx.data["t"] = 0
            state.set_emotion("love")

    elif phase == "love_show":
        t = ctx.data["t"] + step
        ctx.data["t"] = t
        state.set_emotion("love")
        if t >= 5000:
            ctx.data["phase"] = "pansu"
            ctx.data["t"] = 0
            ctx.data["pansu_list"] = random.choices(_PANSU, k=3)
            ctx.data["pansu_i"] = 0

    elif phase == "pansu":
        t = ctx.data["t"] + step
        ctx.data["t"] = t
        pi = ctx.data["pansu_i"]
        state.set_emotion(ctx.data["pansu_list"][pi])
        if t >= 5000:
            pi += 1
            if pi < len(ctx.data["pansu_list"]):
                ctx.data["pansu_i"] = pi
                ctx.data["t"] = 0
            else:
                ctx.data["phase"] = "nopanty"
                ctx.data["t"] = 0
                state.set_emotion("no_panty")

    elif phase == "nopanty":
        t = ctx.data["t"] + step
        ctx.data["t"] = t
        state.set_emotion("no_panty")
        if t >= 4000:
            ctx.data["phase"] = "done"
            state.set_emotion("love")
            import tts
            tts.speak("Всё!")

    elif phase == "done":
        pass
