import random
from PyQt6.QtGui import QGuiApplication

NAME = "Bounce"
INTERVAL = 2500
CLICK_STOPS = True
ESCAPE_STOPS = True


def start(ctx):
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def stop(ctx):
    ctx.state.set_emotion("neutral")
    ctx.state.set_param("ParamBodyAngleZ", 0)
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    screen = QGuiApplication.primaryScreen().availableGeometry()
    sw, sh = screen.width(), screen.height()
    x, y = ctx.window.x(), ctx.window.y()
    w, h = ctx.window.width(), ctx.window.height()
    ctx.state.set_emotion("joy")
    ctx.state.play_motion("Tap@Body", 0, 2)
    bounce_offset = random.randint(-80, 80)
    ty = y - bounce_offset
    ty = max(50, min(sh - h - 50, ty))
    ctx.window.move(x, ty)
    tilt = (bounce_offset / 80.0) * 20.0
    ctx.state.set_param("ParamBodyAngleZ", tilt)
    ctx.state.set_param("ParamBodyAngleX", random.uniform(-5, 5))
