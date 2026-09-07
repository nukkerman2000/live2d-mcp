import random

NAME = "Nagatoro Tease 1"
INTERVAL = 1000
CLICK_STOPS = False
ESCAPE_STOPS = True
REQUIRES_SPRITE = True

_PANSU = ["pansu_shot2", "pansu_shot3"]


def start(ctx):
    ctx.data["pansu_idx"] = 0
    ctx.data["last_time"] = 0
    ctx.state.set_emotion("neutral")


def stop(ctx):
    ctx.state.set_emotion("neutral")


def tick(ctx):
    pass


def click(ctx):
    pansu = _PANSU[ctx.data["pansu_idx"]]
    ctx.state.set_emotion(pansu)
    ctx.data["pansu_idx"] = (ctx.data["pansu_idx"] + 1) % len(_PANSU)


def double_click(ctx):
    ctx.state.set_emotion("no_panty")
