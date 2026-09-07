import random
from PyQt6.QtGui import QGuiApplication

NAME = "Random"
INTERVAL = 2500
CLICK_STOPS = True
ESCAPE_STOPS = True

EMOTIONS = ["joy", "surprise", "love", "amusement", "anger"]
MOTIONS = ["Tap", "Flick", "FlickDown", "Tap@Body", "Flick@Body"]
TARGETS = []


def start(ctx):
    global TARGETS
    screen = QGuiApplication.primaryScreen().availableGeometry()
    sw, sh = screen.width(), screen.height()
    w, h = ctx.window.width(), ctx.window.height()
    TARGETS = [
        (sw - w - 20, 50), (50, sh - h - 100),
        (sw // 2 - w // 2, sh - h - 100), (10, 10),
        (sw - w - 20, sh - h - 100), (sw // 3, 0),
        (sw // 2 - w // 2, sh // 3),
    ]
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def stop(ctx):
    ctx.state.set_emotion("neutral")
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    emotion = random.choice(EMOTIONS)
    motion = random.choice(MOTIONS)
    ctx.state.set_emotion(emotion)
    ctx.state.play_motion(motion, 0, 2)
    tx, ty = random.choice(TARGETS)
    ctx.window.move(tx, ty)
