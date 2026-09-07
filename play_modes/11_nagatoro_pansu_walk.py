import random
from PyQt6.QtGui import QGuiApplication

NAME = "Nagatoro Pansu Walk"
INTERVAL = 2000
CLICK_STOPS = True
ESCAPE_STOPS = True
REQUIRES_SPRITE = True

_PANSU = ["pansu_shot2", "pansu_shot3"]


def start(ctx):
    ctx.data["t"] = 0
    ctx.state.set_visible(True)
    ctx.window.show()
    ctx.state.set_emotion(random.choice(_PANSU))


def stop(ctx):
    ctx.state.set_visible(True)
    ctx.state.set_emotion("neutral")
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    t = ctx.data["t"] + 1
    ctx.data["t"] = t

    if t >= 1:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        sx, sy = screen.width(), screen.height()
        wx, wy = ctx.window.width(), ctx.window.height()
        tx = random.randint(0, max(0, sx - wx))
        ty = random.randint(0, max(0, sy - wy))
        ctx.window.move(tx, ty)
        ctx.state.set_emotion(random.choice(_PANSU))
        ctx.data["t"] = 0
