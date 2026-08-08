"""Moteur pi-gaming : matrice LED HUB75, clavier evdev, classe Game de base.

Trois briques :

- `Display`  : wrap `RGBMatrix` + polices BDF + primitives de dessin.
- `Keyboard` : lit /dev/input/event* dans un thread, pousse les events dans
               une queue non bloquante. Auto-detecte le premier vrai clavier
               (celui qui a KEY_A + KEY_Z + KEY_ENTER dans ses capacites).
- `Game`     : interface a heriter pour chaque jeu (on_key / tick / render).
"""
import os
import queue
import threading

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

try:
    import evdev
except ImportError:  # evdev absent : le module se charge quand meme,
    evdev = None      # Keyboard levera une erreur claire a l'instanciation.


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------- Display ---------------------------------------------------------

class Display:
    """Matrice LED + polices + helpers de dessin.

    Les polices sont chargees depuis `font_cfg` (dict {nom: chemin.bdf}).
    Les noms utilises dans `text(...)` / `text_centered(...)` doivent
    matcher les cles de ce dict.
    """

    def __init__(self, panel_cfg, font_cfg):
        self.matrix = self._build_matrix(panel_cfg)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.width = self.matrix.width
        self.height = self.matrix.height
        self.fonts = {n: self._load_font(p) for n, p in font_cfg.items()}
        self.char_widths = {n: _font_char_width(p) for n, p in font_cfg.items()}

    @staticmethod
    def _build_matrix(panel):
        o = RGBMatrixOptions()
        o.rows = panel["rows"]
        o.cols = panel["cols"]
        o.chain_length = panel["chain_length"]
        o.parallel = panel["parallel"]
        o.gpio_slowdown = panel["gpio_slowdown"]
        o.hardware_mapping = panel["hardware_mapping"]
        o.brightness = panel["brightness"]
        if panel.get("pixel_mapper_config"):
            o.pixel_mapper_config = panel["pixel_mapper_config"]
        if panel.get("disable_hardware_pulsing"):
            o.disable_hardware_pulsing = True
        # rgbmatrix bascule de root a `daemon` apres avoir pris les GPIO ;
        # on desactive pour garder l'acces aux fichiers /home/<user> (mode 700).
        o.drop_privileges = False
        return RGBMatrix(options=o)

    @staticmethod
    def _load_font(rel_path):
        font = graphics.Font()
        path = rel_path if os.path.isabs(rel_path) else os.path.join(BASE_DIR, rel_path)
        font.LoadFont(path)
        return font

    def clear(self):
        self.canvas.Clear()

    def swap(self):
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def text(self, font_name, x, y, color, text):
        graphics.DrawText(self.canvas, self.fonts[font_name], x, y,
                          _to_color(color), text)

    def text_centered(self, font_name, y, color, text, area_x=0, area_w=None):
        if area_w is None:
            area_w = self.width
        cw = self.char_widths[font_name]
        x = area_x + (area_w - len(text) * cw) // 2
        graphics.DrawText(self.canvas, self.fonts[font_name], x, y,
                          _to_color(color), text)

    def pixel(self, x, y, color):
        self.canvas.SetPixel(x, y, *color)

    def rect(self, x, y, w, h, color):
        r, g, b = color
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.canvas.SetPixel(xx, yy, r, g, b)


def _to_color(c):
    if isinstance(c, graphics.Color):
        return c
    return graphics.Color(*c)


def _font_char_width(rel_path):
    # Nos BDF sont monospace : "5x7.bdf" -> largeur 5 px/glyph.
    return int(os.path.basename(rel_path).split("x", 1)[0])


# ---------- Keyboard --------------------------------------------------------

class KeyEvent:
    """Un appui touche. `char` est la lettre/chiffre (A-Z, 0-9) ou None
    pour les touches speciales (fleches, entree, esc, ...).
    """
    __slots__ = ("code", "name", "char")

    def __init__(self, code, name, char):
        self.code = code
        self.name = name
        self.char = char

    def __repr__(self):
        return f"KeyEvent(name={self.name}, char={self.char})"


class Keyboard:
    """Lit un clavier USB via evdev dans un thread background.

    Utilisation :
        kb = Keyboard()          # auto-detection
        kb.start()
        ...
        for ev in kb.poll():     # non bloquant, retourne les events KEY_DOWN
            handle(ev)
    """

    def __init__(self, device_path=None):
        if evdev is None:
            raise RuntimeError(
                "Le paquet Python 'evdev' est manquant. "
                "Lance install.sh ou : pip install evdev"
            )
        self.device = self._open(device_path)
        self.queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = None

    @staticmethod
    def _open(device_path):
        if device_path:
            return evdev.InputDevice(device_path)
        # Auto-detection : un vrai clavier expose au moins A + Z + ENTER.
        # (Un pave numerique isole ou une manette n'aurait pas KEY_A.)
        required = {evdev.ecodes.KEY_A, evdev.ecodes.KEY_Z, evdev.ecodes.KEY_ENTER}
        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            caps = set(dev.capabilities().get(evdev.ecodes.EV_KEY, []))
            if required.issubset(caps):
                return dev
            dev.close()
        raise RuntimeError(
            "Aucun clavier detecte dans /dev/input/. "
            "Renseigne `keyboard.device` (ex. /dev/input/event3) dans config.json."
        )

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        for event in self.device.read_loop():
            if self._stop.is_set():
                return
            if event.type != evdev.ecodes.EV_KEY:
                continue
            ke = evdev.categorize(event)
            # 1 = key down, 2 = key hold (repeat), 0 = key up.
            # On ne remonte que le down pour eviter les rebonds.
            if ke.keystate != ke.key_down:
                continue
            name = ke.keycode if isinstance(ke.keycode, str) else ke.keycode[0]
            self.queue.put(KeyEvent(event.code, name, _keyname_to_char(name)))

    def poll(self):
        """Vide la queue et retourne la liste des events. Non bloquant."""
        events = []
        while True:
            try:
                events.append(self.queue.get_nowait())
            except queue.Empty:
                return events


def _keyname_to_char(name):
    """`KEY_A` -> 'A', `KEY_1` -> '1', autres -> None."""
    if name.startswith("KEY_") and len(name) == 5:
        c = name[4]
        if c.isalnum():
            return c
    return None


# ---------- Game ------------------------------------------------------------

class Game:
    """Classe de base d'un jeu. A heriter dans games/<mon_jeu>.py.

    - `name`         : nom court affiche au menu (attribut de classe).
    - `on_key(ev)`   : appele pour chaque KeyEvent recu (une seule fois par appui).
    - `tick(dt)`     : mise a jour de l'etat (dt en secondes depuis la frame precedente).
    - `render(disp)` : dessin sur le canvas (le clear + swap sont geres par la loop).
    """
    name = "SANS NOM"

    def on_key(self, event):
        pass

    def tick(self, dt):
        pass

    def render(self, display):
        pass
