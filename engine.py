"""pi-gaming engine: LED matrix display, evdev keyboard, base Game class.

Three building blocks:

- `Display`  : wraps `RGBMatrix` + BDF fonts + drawing primitives.
- `Keyboard` : reads /dev/input/event* in a background thread, pushes events
               to a non-blocking queue. Auto-detects the first real keyboard
               (one whose capabilities include KEY_A + KEY_Z + KEY_ENTER).
- `Game`     : base class each game inherits from (on_key / tick / render).
"""
import os
import queue
import threading

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

try:
    import evdev
except ImportError:  # If evdev is missing the module still imports;
    evdev = None      # Keyboard raises a clear error on instantiation.


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------- Display ---------------------------------------------------------

class Display:
    """LED matrix + fonts + drawing helpers.

    Fonts are loaded from `font_cfg` (a `{name: bdf_path}` dict). The names
    used later in `text(...)` / `text_centered(...)` must match those keys.
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
        # rgbmatrix drops from root to `daemon` after grabbing the GPIOs;
        # we disable that so we keep access to /home/<user> files (mode 700).
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

    def sprite(self, sprite, x, y, color):
        """Draw a bitmap sprite (list of strings, '#' = lit pixel)."""
        r, g, b = color
        for row, line in enumerate(sprite):
            for col, ch in enumerate(line):
                if ch == "#":
                    self.canvas.SetPixel(x + col, y + row, r, g, b)


def _to_color(c):
    if isinstance(c, graphics.Color):
        return c
    return graphics.Color(*c)


def _font_char_width(rel_path):
    # Our BDF fonts are monospace: "5x7.bdf" -> 5 px per glyph.
    return int(os.path.basename(rel_path).split("x", 1)[0])


# ---------- Keyboard --------------------------------------------------------

# evdev reports physical keycodes (KEY_Q = the key at the top-left of the
# home row, regardless of the label printed on it). With an OS configured for
# US QWERTY and a physical French keyboard plugged in, the key labeled "A"
# generates KEY_Q. This dict remaps keycode -> character seen by the user.
#
# Digits (KEY_1..KEY_0) are left at their default: they already produce the
# expected digit regardless of layout (no Shift needed), which is exactly
# what we want for the "Azerty/Numeric" mode.
LAYOUTS = {
    "qwerty": {},  # no remap: default behavior.
    "azerty": {
        # Top row (AZERTY: A Z E R T Y ...)
        "KEY_Q": "A", "KEY_W": "Z",
        # Home row (AZERTY: Q S D F G H J K L M)
        "KEY_A": "Q",
        "KEY_SEMICOLON": "M",
        # Bottom row (AZERTY: W X C V B N , ; : !)
        "KEY_Z": "W",
        "KEY_M": ",",
        "KEY_COMMA": ";",
        "KEY_DOT": ":",
        "KEY_SLASH": "!",
    },
}


class KeyEvent:
    """A single key press. `char` is the letter/digit (A-Z, 0-9) or None
    for special keys (arrows, enter, esc, ...).
    """
    __slots__ = ("code", "name", "char")

    def __init__(self, code, name, char):
        self.code = code
        self.name = name
        self.char = char

    def __repr__(self):
        return f"KeyEvent(name={self.name}, char={self.char})"


class Keyboard:
    """Reads a USB keyboard through evdev in a background thread.

    Usage:
        kb = Keyboard()          # auto-detect
        kb.start()
        ...
        for ev in kb.poll():     # non-blocking, returns KEY_DOWN events
            handle(ev)
    """

    def __init__(self, device_path=None, layout="qwerty"):
        if evdev is None:
            raise RuntimeError(
                "The 'evdev' Python package is missing. "
                "Run install.sh or: pip install evdev"
            )
        self.device = self._open(device_path)
        self.layout = LAYOUTS.get(layout, {})
        self.queue = queue.Queue()
        # Set of currently-held key names (updated on key down/up in the
        # background thread). Read via is_held(name) for hold-based games.
        # A plain set is fine here: single-op add/discard vs `in` reads are
        # atomic under the CPython GIL, we never iterate while mutating.
        self._held = set()
        self._stop = threading.Event()
        self._thread = None

    def is_held(self, name):
        return name in self._held

    @staticmethod
    def _open(device_path):
        if device_path:
            return evdev.InputDevice(device_path)
        # Auto-detect: a real keyboard exposes at least A + Z + ENTER.
        # (A stand-alone numpad or a gamepad wouldn't have KEY_A.)
        required = {evdev.ecodes.KEY_A, evdev.ecodes.KEY_Z, evdev.ecodes.KEY_ENTER}
        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            caps = set(dev.capabilities().get(evdev.ecodes.EV_KEY, []))
            if required.issubset(caps):
                return dev
            dev.close()
        raise RuntimeError(
            "No keyboard detected in /dev/input/. "
            "Set `keyboard.device` (e.g. /dev/input/event3) in config.json."
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
            name = ke.keycode if isinstance(ke.keycode, str) else ke.keycode[0]
            # 1 = key down, 2 = key hold (autorepeat), 0 = key up.
            # We forward only key-down to the event queue to avoid bouncing,
            # but we track key-up too so is_held() stays accurate for
            # hold-based games. key_hold (autorepeat) is ignored: the key is
            # already in _held from the initial key_down.
            if ke.keystate == ke.key_down:
                self._held.add(name)
                char = self.layout.get(name) or _keyname_to_char(name)
                self.queue.put(KeyEvent(event.code, name, char))
            elif ke.keystate == ke.key_up:
                self._held.discard(name)

    def poll(self):
        """Drain the queue and return the events. Non-blocking."""
        events = []
        while True:
            try:
                events.append(self.queue.get_nowait())
            except queue.Empty:
                return events


def _keyname_to_char(name):
    """`KEY_A` -> 'A', `KEY_1` -> '1', anything else -> None."""
    if name.startswith("KEY_") and len(name) == 5:
        c = name[4]
        if c.isalnum():
            return c
    return None


# ---------- Game ------------------------------------------------------------

class Game:
    """Base class for a game. Subclass it in games/<my_game>.py.

    - `name`         : short label shown in the menu (class attribute).
    - `on_key(ev)`   : called once per received KeyEvent.
    - `tick(dt)`     : state update (dt in seconds since the previous frame).
    - `render(disp)` : draw on the canvas (clear + swap are handled by the loop).

    `self.keyboard` is injected by the main loop before the first tick,
    for games that need `keyboard.is_held(name)` (hold-based mechanics).
    """
    name = "SANS NOM"
    keyboard = None

    def on_key(self, event):
        pass

    def tick(self, dt):
        pass

    def render(self, display):
        pass
