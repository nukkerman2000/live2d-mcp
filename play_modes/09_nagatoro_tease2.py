import random
from PyQt6.QtGui import QGuiApplication

NAME = "Nagatoro Tease 2"
INTERVAL = 1000
CLICK_STOPS = True
ESCAPE_STOPS = True
REQUIRES_SPRITE = True

_PANSU = ["pansu_shot2", "pansu_shot3"]


def start(ctx):
    ctx.data["phase"] = "intro"
    ctx.data["t"] = 0
    ctx.state.set_visible(True)
    ctx.window.show()
    ctx.state.set_emotion("love")


def stop(ctx):
    ctx.state.set_visible(True)
    ctx.state.set_emotion("neutral")
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    phase = ctx.data["phase"]
    t = ctx.data["t"] + 1
    ctx.data["t"] = t
    w = ctx.window

    if phase == "intro":
        if t >= 2:
            ctx.state.set_visible(False)
            w.hide()
            ctx.data["phase"] = "hide"
            ctx.data["t"] = 0

    elif phase == "hide":
        if t >= 10:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            sx, sy = screen.width(), screen.height()
            wx, wy = w.width(), w.height()
            tx = random.randint(0, max(0, sx - wx))
            ty = random.randint(0, max(0, sy - wy))
            ctx.data["appear_x"] = tx
            ctx.data["appear_y"] = ty
            w.move(tx, ty)
            ctx.state.set_visible(True)
            w.show()
            ctx.state.set_emotion("love")
            ctx.data["phase"] = "show_love"
            ctx.data["t"] = 0

    elif phase == "show_love":
        if t >= 3:
            ctx.state.set_emotion(random.choice(_PANSU))
            ctx.data["phase"] = "show_pansu"
            ctx.data["t"] = 0

    elif phase == "show_pansu":
        if t >= 5:
            ctx.state.set_emotion("no_panty")
            ctx.data["phase"] = "show_nopanty"
            ctx.data["t"] = 0

    elif phase == "show_nopanty":
        if t >= 5:
            ctx.state.set_visible(False)
            w.hide()
            ctx.data["phase"] = "hide"
            ctx.data["t"] = 0
