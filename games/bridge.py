"""Co-op game: bridge.

Two kids hold up a plank so a little character can stand on it.
- Left kid holds LEFT SHIFT: the left post pushes the plank up on the left.
- Right kid holds RIGHT SHIFT: the right post pushes it up on the right.
- If one side is released, that side of the plank slowly drops.
- If both are released, both sides drop.
- When the middle of the plank has fallen too low, the character slips off.

Pure coop: neither kid can keep the character alive alone. Score = time
survived with both kids holding.
"""
from engine import Game


LEFT_KEY = "KEY_LEFTSHIFT"
RIGHT_KEY = "KEY_RIGHTSHIFT"

BEAM_LEFT_X = 12
BEAM_RIGHT_X = 179
BEAM_Y_UP = 14            # highest y (top of screen)
BEAM_Y_DOWN = 30          # lowest y (character falls at this level)

LIFT_RATE = 3.0           # units per second when the side is held (0..1)
FALL_RATE = 1.2           # units per second when it is released

FALL_THRESHOLD = 0.25     # center height under which the character slips

DEATH_HOLD_S = 1.0
SCORE_PER_SECOND = 5

CHAR_SPRITE = [
    ".#.",
    "###",
    ".#.",
    "#.#",
]
CHAR_W = 3
CHAR_H = 4

POST_W = 3
POST_TOP = BEAM_Y_UP - 2
POST_BOTTOM = 31

C_BEAM = (200, 180, 100)
C_BEAM_LOW = (255, 100, 80)
C_CHAR = (255, 220, 0)
C_CHAR_FALLING = (255, 60, 60)
C_POST_HELD = (0, 220, 120)
C_POST_LOOSE = (120, 60, 60)
C_LABEL_HELD = (0, 220, 120)
C_LABEL_LOOSE = (120, 120, 120)
C_SCORE = (120, 120, 120)
C_DEATH = (255, 80, 80)


def _lerp(a, b, t):
    return a + (b - a) * t


class BridgeGame(Game):
    name = "PONT"

    def __init__(self):
        self.left_h = 1.0
        self.right_h = 1.0
        self.score_time = 0.0
        self.death_timer = 0.0

    def tick(self, dt):
        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self._restart()
            return

        kb = self.keyboard
        left_held = kb is not None and kb.is_held(LEFT_KEY)
        right_held = kb is not None and kb.is_held(RIGHT_KEY)

        self.left_h = _clamp01(self.left_h
                               + (LIFT_RATE if left_held else -FALL_RATE) * dt)
        self.right_h = _clamp01(self.right_h
                                + (LIFT_RATE if right_held else -FALL_RATE) * dt)

        center_h = (self.left_h + self.right_h) / 2
        if center_h < FALL_THRESHOLD:
            self.death_timer = DEATH_HOLD_S
            return

        # Score only counts when BOTH sides are actively held: co-op reward.
        if left_held and right_held:
            self.score_time += dt

    def _restart(self):
        self.left_h = 1.0
        self.right_h = 1.0
        self.score_time = 0.0

    def render(self, display):
        kb = self.keyboard
        left_held = kb is not None and kb.is_held(LEFT_KEY)
        right_held = kb is not None and kb.is_held(RIGHT_KEY)

        left_y = int(round(_lerp(BEAM_Y_DOWN, BEAM_Y_UP, self.left_h)))
        right_y = int(round(_lerp(BEAM_Y_DOWN, BEAM_Y_UP, self.right_h)))

        # Posts on each edge, colored per hold state (visual cue for the kids).
        left_color = C_POST_HELD if left_held else C_POST_LOOSE
        right_color = C_POST_HELD if right_held else C_POST_LOOSE
        display.rect(0, POST_TOP, POST_W, POST_BOTTOM - POST_TOP + 1, left_color)
        display.rect(display.width - POST_W, POST_TOP, POST_W,
                     POST_BOTTOM - POST_TOP + 1, right_color)

        # Plank as a straight line from (BEAM_LEFT_X, left_y) to (BEAM_RIGHT_X, right_y).
        center_h = (self.left_h + self.right_h) / 2
        beam_color = C_BEAM_LOW if center_h < 0.5 else C_BEAM
        dx = BEAM_RIGHT_X - BEAM_LEFT_X
        for x in range(BEAM_LEFT_X, BEAM_RIGHT_X + 1):
            t = (x - BEAM_LEFT_X) / dx
            y = int(round(left_y + t * (right_y - left_y)))
            display.pixel(x, y, beam_color)

        # Character sits at the middle of the plank.
        char_x = (BEAM_LEFT_X + BEAM_RIGHT_X) // 2 - CHAR_W // 2
        char_center_y = (left_y + right_y) // 2
        char_y = char_center_y - CHAR_H
        char_color = C_CHAR_FALLING if self.death_timer > 0 else C_CHAR
        display.sprite(CHAR_SPRITE, char_x, char_y, char_color)

        # Small key hint under each post (Q on the far left, P on the far right).
        # The letters don't matter to a 3-year-old; the COLOR does (green = ok).
        display.text("small", 5, 7,
                     C_LABEL_HELD if left_held else C_LABEL_LOOSE, "Q")
        display.text("small", display.width - 10, 7,
                     C_LABEL_HELD if right_held else C_LABEL_LOOSE, "P")

        # Score in the top middle.
        score_txt = str(int(self.score_time * SCORE_PER_SECOND))
        display.text_centered("small", 7, C_SCORE, score_txt)

        if self.death_timer > 0:
            display.text_centered("small", 15, C_DEATH, "AIE !")


def _clamp01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x
