#!/usr/bin/env python3
"""pi-gaming - plateforme de mini-jeux educatifs sur matrice LED HUB75.

Squelette :
- 3 panneaux LED 64x32 chaines (comme worldclock) = 192x32 pixels.
- Clavier USB lu via evdev (thread background).
- Menu de selection (fleches gauche/droite, Entree pour lancer,
  Echap pour revenir au menu).

Ajouter un jeu : voir `games/__init__.py`.

Toutes les cles ci-dessous ont un defaut raisonnable. `config.json`
ne contient QUE ce que tu veux surcharger (deep-merge).
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
        # None => auto-detection du premier vrai clavier dans /dev/input.
        # Sinon, chemin explicite (ex. "/dev/input/event3").
        "device": None,
        # "qwerty" ou "azerty". "azerty" = clavier FR branche sur un OS US :
        # la touche marquee "A" renvoie 'A', "M" renvoie 'M', etc. Les
        # chiffres du haut restent des chiffres (pas besoin de Shift).
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


# ---------- Menu de selection -----------------------------------------------

class Menu(Game):
    """Ecran de selection. Signale son choix via `self.selected`."""
    name = "MENU"

    def __init__(self, games):
        self.games = games
        self.index = 0
        self.selected = None

    def on_key(self, event):
        # `char` est post-layout : les raccourcis A/D marchent en qwerty
        # comme en azerty (l'user tape la touche qui affiche A ou D).
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


# ---------- Boucle de scene -------------------------------------------------

def run_scene(scene, display, keyboard, cfg):
    """Fait tourner une scene jusqu'a Echap (ou choix, pour le menu).

    Retour :
    - Menu : classe du jeu selectionne, ou None si Echap.
    - Jeu  : None (retour au menu).
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


# ---------- Ecran "aucun jeu" -----------------------------------------------

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
            if next_cls is None:  # Echap dans le menu = on quitte.
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
