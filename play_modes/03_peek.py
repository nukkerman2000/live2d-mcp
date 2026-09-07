import random
from PyQt6.QtGui import QGuiApplication

NAME = "Peek"
INTERVAL = 2500
CLICK_STOPS = True
ESCAPE_STOPS = True


def start(ctx):
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def stop(ctx):
    ctx.state.set_emotion("neutral")
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    screen = QGuiApplication.primaryScreen().availableGeometry()
    sw, sh = screen.width(), screen.height()
    w, h = ctx.window.width(), ctx.window.height()
    edges = [
        (random.randint(0, sw - w), 0),
        (random.randint(0, sw - w), sh - h),
        (0, random.randint(0, sh - h)),
        (sw - w, random.randint(0, sh - h)),
    ]
    tx, ty = random.choice(edges)
    ctx.window.move(tx, ty)
    ctx.state.set_emotion("surprise")
    ctx.state.play_motion("Flick", 0, 2)
