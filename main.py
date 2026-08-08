#!/usr/bin/env python3
"""pi-gaming - educational mini-games platform on a HUB75 LED matrix.

Skeleton:
- 3 chained 64x32 LED panels (same as worldclock) = 192x32 pixels.
- USB keyboard read through evdev (background thread).
- Selection menu (left/right arrows, Enter to launch, Esc to go back).

See `games/__init__.py` to add a game.

All the keys below have sensible defaults. `config.json` only carries what
you want to override (deep-merged onto DEFAULTS).
"""
import json
import os
import time

from engine import BASE_DIR, Display, Game, Keyboard
from games import GAMES

DEFAULTS = {
    "panel": {
        "rows": 32,
        "cols": 64,
        "chain_length": 3,
        "parallel": 1,
        "gpio_slowdown": 2,
        "hardware_mapping": "regular",
        "pixel_mapper_config": "",
        "disable_hardware_pulsing": False,
        "brightness": 70,
    },
    "font": {
        "small": "fonts/5x7.bdf",
        "medium": "fonts/6x10.bdf",
        "big": "fonts/7x13.bdf",
    },
    "keyboard": {
        # None => auto-detect the first real keyboard under /dev/input.
        # Otherwise, an explicit path (e.g. "/dev/input/event3").
        "device": None,
        # "qwerty" or "azerty". "azerty" = French keyboard on a US OS:
        # the key labeled "A" produces 'A', "M" produces 'M', etc. The top
        # row still produces digits (no Shift required).
        "layout": "qwerty",
    },
    "fps": 30,
}


def deep_merge(default, override):
    result = dict(default)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config():
    path = os.path.join(BASE_DIR, "config.json")
    if not os.path.exists(path):
        return dict(DEFAULTS)
    with open(path, encoding="utf-8") as f:
        return deep_merge(DEFAULTS, json.load(f))


# ---------- Selection menu --------------------------------------------------

class Menu(Game):
    """Selection screen. Signals its choice through `self.selected`."""
    name = "MENU"

    def __init__(self, games):
        self.games = games
        self.index = 0
        self.selected = None

    def on_key(self, event):
        # `char` is post-layout: the A/D shortcuts work identically under
        # qwerty and azerty (the user types the key labeled A or D).
        if event.name == "KEY_LEFT" or event.char == "A":
            self.index = (self.index - 1) % len(self.games)
        elif event.name == "KEY_RIGHT" or event.char == "D":
            self.index = (self.index + 1) % len(self.games)
        elif event.name in ("KEY_ENTER", "KEY_KPENTER", "KEY_SPACE"):
            self.selected = self.games[self.index]

    def render(self, display):
        display.text_centered("small", 8, (0, 200, 255), "CHOISIS UN JEU")
        display.text_centered("big", 22, (255, 200, 0),
                              self.games[self.index].name)
        display.text_centered("small", 31, (120, 120, 120),
                              f"< {self.index + 1}/{len(self.games)} >")


# ---------- Scene loop ------------------------------------------------------

def run_scene(scene, display, keyboard, cfg):
    """Run a scene until Esc (or, for the menu, until a game is picked).

    Returns:
    - Menu: the selected game class, or None on Esc.
    - Game: None (back to menu).
    """
    frame_time = 1.0 / cfg["fps"]
    last_t = time.monotonic()
    is_menu = isinstance(scene, Menu)

    while True:
        now = time.monotonic()
        dt = now - last_t
        last_t = now

        for event in keyboard.poll():
            if event.name == "KEY_ESC":
                return scene.selected if is_menu else None
            scene.on_key(event)
            if is_menu and scene.selected is not None:
                return scene.selected

        scene.tick(dt)
        display.clear()
        scene.render(display)
        display.swap()

        elapsed = time.monotonic() - now
        if elapsed < frame_time:
            time.sleep(frame_time - elapsed)


# ---------- "No game" screen ------------------------------------------------

def _no_games_screen(display):
    display.clear()
    display.text_centered("small", 12, (255, 80, 80), "AUCUN JEU")
    display.text_centered("small", 24, (120, 120, 120), "games/")
    display.swap()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


# ---------- Main ------------------------------------------------------------

def main():
    cfg = load_config()
    display = Display(cfg["panel"], cfg["font"])
    keyboard = Keyboard(cfg["keyboard"]["device"], cfg["keyboard"]["layout"])
    keyboard.start()

    if not GAMES:
        _no_games_screen(display)
        return

    menu = Menu(GAMES)
    try:
        while True:
            next_cls = run_scene(menu, display, keyboard, cfg)
            if next_cls is None:  # Esc in the menu = exit.
                break
            menu.selected = None
            run_scene(next_cls(), display, keyboard, cfg)
    except KeyboardInterrupt:
        pass
    finally:
        display.clear()
        display.swap()
        keyboard.stop()


if __name__ == "__main__":
    main()
