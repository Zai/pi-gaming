"""Co-op game: rowing boat.

A boat crosses the river from left to right. Each kid controls one oar:
- Left kid taps LEFT SHIFT (left oar).
- Right kid taps RIGHT SHIFT (right oar).

A stroke only counts when it ALTERNATES with the previous one — so both
kids must take turns. Same-side spam does not move the boat forward; it
makes it wobble in place (visual feedback for the mistake).

Reach the right edge -> "BRAVO !" + a new crossing starts. Score = number
of successful crossings.
"""
from engine import Game


LEFT_KEY = "KEY_LEFTSHIFT"
RIGHT_KEY = "KEY_RIGHTSHIFT"

BOAT_START_X = 6
BOAT_GOAL_X = 174         # right edge threshold (screen is 192 wide)
BOAT_Y = 18
STROKE_ADVANCE = 12       # pixels gained per correctly-alternated stroke
WOBBLE_AMPLITUDE = 3
WOBBLE_DECAY = 4.0        # per second

WATER_Y = 26
WAVE_STEP = 8             # spacing between wave crests

FINISH_HOLD_S = 1.2

# BOAT_SPRITE (14 wide x 5 tall): a small canoe with a sail-ish mark.
BOAT_SPRITE = [
    "......##......",
    "......##......",
    ".############.",
    "##############",
    ".############.",
]
BOAT_W = 14
BOAT_H = 5

FLAG_SPRITE = [
    "###",
    "#..",
    "#..",
    "#..",
    "#..",
]

C_BOAT = (255, 200, 0)
C_BOAT_WOBBLE = (255, 100, 80)
C_WATER = (0, 100, 200)
C_FLAG = (0, 220, 120)
C_LABEL_ACTIVE = (0, 220, 120)
C_LABEL_IDLE = (120, 120, 120)
C_SCORE = (120, 120, 120)
C_FINISH = (0, 220, 120)


class BoatGame(Game):
    name = "BATEAU"

    def __init__(self):
        self.x = float(BOAT_START_X)
        self.last_side = None      # "L", "R", or None (next stroke counts either way)
        self.wobble = 0.0
        self.finish_timer = 0.0
        self.score = 0
        self._flash_side = None    # highlight the last active oar briefly
        self._flash_timer = 0.0

    def on_key(self, event):
        if self.finish_timer > 0:
            return
        if event.name == LEFT_KEY:
            self._stroke("L")
        elif event.name == RIGHT_KEY:
            self._stroke("R")

    def _stroke(self, side):
        self._flash_side = side
        self._flash_timer = 0.15
        if self.last_side == side:
            # Same side twice: wobble instead of advancing.
            self.wobble = WOBBLE_AMPLITUDE
            return
        self.last_side = side
        self.x += STROKE_ADVANCE
        if self.x >= BOAT_GOAL_X:
            self.x = float(BOAT_GOAL_X)
            self.score += 1
            self.finish_timer = FINISH_HOLD_S

    def tick(self, dt):
        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt)
            if self._flash_timer <= 0:
                self._flash_side = None
        if self.wobble > 0:
            self.wobble = max(0.0, self.wobble - WOBBLE_DECAY * dt)
        if self.finish_timer > 0:
            self.finish_timer -= dt
            if self.finish_timer <= 0:
                self._restart()

    def _restart(self):
        self.x = float(BOAT_START_X)
        self.last_side = None
        self.wobble = 0.0

    def render(self, display):
        # Water: dashed line so movement feels real.
        for x in range(0, display.width, WAVE_STEP):
            display.pixel(x, WATER_Y, C_WATER)
            display.pixel(x + 1, WATER_Y, C_WATER)

        # Finish flag on the right edge.
        display.sprite(FLAG_SPRITE, BOAT_GOAL_X + BOAT_W + 1,
                       WATER_Y - len(FLAG_SPRITE), C_FLAG)

        # Boat with a tiny horizontal wobble on same-side spam.
        boat_x = int(round(self.x))
        if self.wobble > 0:
            boat_x += 1 if (int(self.wobble * 8) % 2) else -1
        boat_color = C_BOAT_WOBBLE if self.wobble > 0 else C_BOAT
        display.sprite(BOAT_SPRITE, boat_x, BOAT_Y, boat_color)

        # Oar labels top-left / top-right. Green flash on the side that just
        # rowed, gray otherwise.
        left_color = (C_LABEL_ACTIVE if self._flash_side == "L"
                      else C_LABEL_IDLE)
        right_color = (C_LABEL_ACTIVE if self._flash_side == "R"
                       else C_LABEL_IDLE)
        display.text("small", 2, 7, left_color, "Q")
        display.text("small", display.width - 7, 7, right_color, "P")

        # Score top-middle: number of crossings.
        score_txt = str(self.score)
        display.text_centered("small", 7, C_SCORE, score_txt)

        if self.finish_timer > 0:
            display.text_centered("small", 15, C_FINISH, "BRAVO !")
