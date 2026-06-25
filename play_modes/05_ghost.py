import math
import random
from PyQt6.QtGui import QGuiApplication

NAME = "Ghost"
INTERVAL = 500
CLICK_STOPS = True
ESCAPE_STOPS = True


def start(ctx):
    ctx.state.set_visible(False)
    ctx.window.hide()
    ctx.data["phase"] = "hide_start"
    ctx.data["t"] = 0
    ctx.data["cycle"] = 0
    ctx.data["y"] = ctx.window.y()


def stop(ctx):
    ctx.state.set_visible(True)
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    phase = ctx.data["phase"]
    t = ctx.data["t"]
    w = ctx.window
    state = ctx.state

    if phase == "hide_start":
        t += 500
        if t >= 30000:
            ctx.data["phase"] = "slide"
            ctx.data["t"] = 0
            w.move(-w.width(), ctx.data["y"])
            state.set_visible(True)
            w.show()
            w.setWindowOpacity(1.0)
            state.set_emotion("surprise")
            ctx.data["interval"] = 30
    elif phase == "slide":
        t += 30
        progress = min(t / 4000.0, 1.0)
        sw = QGuiApplication.primaryScreen().availableGeometry().width()
        cx = -w.width() + (sw + w.width() * 2) * progress
        w.move(int(cx), ctx.data["y"])
        if progress > 0.7:
            w.setWindowOpacity(max(0.0, 1.0 - (progress - 0.7) / 0.3))
        if progress >= 1.0:
            w.hide()
            state.set_visible(False)
            w.setWindowOpacity(1.0)
            ctx.data["phase"] = "short_show"
            ctx.data["t"] = 0
            sw = QGuiApplication.primaryScreen().availableGeometry().width()
            w.move(sw - w.width(), ctx.data["y"])
            state.set_visible(True)
            w.show()
            state.set_emotion("joy")
            state.play_motion("Tap", 0, 2)
            ctx.data["interval"] = 500
    elif phase == "short_show":
        t += 500
        sway = math.sin(t / 1000.0 * math.pi) * 15
        sw = QGuiApplication.primaryScreen().availableGeometry().width()
        w.move(int(sw - w.width() + sway), ctx.data["y"])
        state.set_emotion(random.choice(["joy", "amusement", "love"]))
        state.set_param("ParamBodyAngleZ", random.uniform(-5, 5))
        if t >= 10000:
            ctx.data["phase"] = "short_fade"
            ctx.data["t"] = 0
            ctx.data["interval"] = 30
    elif phase == "short_fade":
        t += 30
        progress = min(t / 10000.0, 1.0)
        w.setWindowOpacity(max(0.0, 1.0 - progress))
        sway = math.sin((t + 500) / 1000.0 * math.pi) * 10
        sw = QGuiApplication.primaryScreen().availableGeometry().width()
        w.move(int(sw - w.width() + sway), ctx.data["y"])
        if progress >= 1.0:
            w.hide()
            state.set_visible(False)
            w.setWindowOpacity(1.0)
            ctx.data["cycle"] += 1
            if ctx.data["cycle"] >= 3:
                ctx.data["phase"] = "hide_mid"
                ctx.data["t"] = 0
                ctx.data["interval"] = 500
            else:
                ctx.data["phase"] = "short_show"
                ctx.data["t"] = 0
                sw = QGuiApplication.primaryScreen().availableGeometry().width()
                w.move(sw - w.width(), ctx.data["y"])
                state.set_visible(True)
                w.show()
                w.setWindowOpacity(1.0)
                state.set_emotion("joy")
                state.play_motion("Tap", 0, 2)
                ctx.data["interval"] = 500
    elif phase == "hide_mid":
        t += 500
        if t >= 30000:
            ctx.data["phase"] = "slide"
            ctx.data["t"] = 0
            ctx.data["cycle"] = 0
            w.move(-w.width(), ctx.data["y"])
            state.set_visible(True)
            w.show()
            w.setWindowOpacity(1.0)
            state.set_emotion("surprise")
            ctx.data["interval"] = 30

    ctx.data["t"] = t
