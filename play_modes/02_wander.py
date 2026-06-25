import random
from PyQt6.QtGui import QGuiApplication

NAME = "Wander"
INTERVAL = 2500
CLICK_STOPS = True
ESCAPE_STOPS = True

EMOTIONS = ["joy", "surprise", "love", "amusement", "anger"]
MOTIONS = ["Tap", "Flick", "FlickDown", "Tap@Body", "Flick@Body"]


def start(ctx):
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def stop(ctx):
    ctx.state.set_emotion("neutral")
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    screen = QGuiApplication.primaryScreen().availableGeometry()
    sw, sh = screen.width(), screen.height()
    x, y = ctx.window.x(), ctx.window.y()
    w, h = ctx.window.width(), ctx.window.height()
    ctx.state.set_emotion(random.choice(EMOTIONS))
    ctx.state.play_motion(random.choice(MOTIONS), 0, 2)
    tx = x + random.randint(-150, 150)
    ty = y + random.randint(-100, 100)
    tx = max(0, min(sw - w, tx))
    ty = max(0, min(sh - h, ty))
    ctx.window.move(tx, ty)
