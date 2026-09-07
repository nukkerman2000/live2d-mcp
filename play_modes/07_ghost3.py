import random

NAME = "Ghost3"
INTERVAL = 15
CLICK_STOPS = False
ESCAPE_STOPS = False


def start(ctx):
    ctx.state.set_visible(True)
    ctx.window.show()
    ctx.window.setWindowOpacity(0.0)
    ctx.data["phase"] = "fadein"
    ctx.data["t"] = 0


def stop(ctx):
    ctx.state.set_visible(True)
    ctx.window.show()
    ctx.window.setWindowOpacity(1.0)


def tick(ctx):
    phase = ctx.data["phase"]
    t = ctx.data["t"]
    step = ctx.data.get("interval", 15)
    w = ctx.window
    state = ctx.state

    if phase == "fadein":
        t += step
        progress = min(t / 1000.0, 1.0)
        w.setWindowOpacity(progress)
        if progress >= 1.0:
            ctx.data["phase"] = "show"
            ctx.data["t"] = 0
            ctx.data["interval"] = 500
    elif phase == "show":
        t += 500
        state.set_emotion(random.choice(["joy", "amusement", "love"]))
        state.set_param("ParamBodyAngleZ", random.uniform(-3, 3))
        if t >= 3000:
            ctx.data["phase"] = "fadeout"
            ctx.data["t"] = 0
            ctx.data["interval"] = 15
    elif phase == "fadeout":
        t += step
        progress = min(t / 1000.0, 1.0)
        w.setWindowOpacity(max(0.0, 1.0 - progress))
        if progress >= 1.0:
            ctx.data["phase"] = "fadein"
            ctx.data["t"] = 0
            ctx.data["interval"] = 15

    ctx.data["t"] = t
