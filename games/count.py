"""Game: count the sticks.

Show N vertical sticks (1 to 5). The child presses the matching digit
key on the top row. Right: green flash + "BRAVO !" then a new count.
Wrong: soft red flash, same count stays so the child can retry.
"""
import random

from engine import Game


MIN_COUNT = 1
MAX_COUNT = 5

STICK_W = 5
STICK_H = 20
STICK_GAP = 12
STICK_Y = 9

_STATE_IDLE = "idle"
_STATE_CORRECT = "correct"
_STATE_WRONG = "wrong"

_CORRECT_HOLD_S = 0.7
_WRONG_HOLD_S = 0.3

C_STICK = (255, 200, 0)
C_STICK_CORRECT = (0, 255, 100)
C_STICK_WRONG = (255, 100, 100)
C_TOP_IDLE = (0, 200, 255)
C_TOP_CORRECT = (0, 255, 100)
C_TOP_WRONG = (255, 100, 100)
C_SCORE = (120, 120, 120)


class CountGame(Game):
    name = "COMPTE"

    def __init__(self):
        self.count = random.randint(MIN_COUNT, MAX_COUNT)
        self.state = _STATE_IDLE
        self.timer = 0.0
        self.score = 0

    def _pick_new_count(self):
        # Avoid repeating the same value back-to-back.
        pool = [n for n in range(MIN_COUNT, MAX_COUNT + 1) if n != self.count]
        self.count = random.choice(pool)

    def on_key(self, event):
        if self.state != _STATE_IDLE or event.char is None:
            return
        if not event.char.isdigit():
            return
        if int(event.char) == self.count:
            self.state = _STATE_CORRECT
            self.timer = _CORRECT_HOLD_S
            self.score += 1
        else:
            self.state = _STATE_WRONG
            self.timer = _WRONG_HOLD_S

    def tick(self, dt):
        if self.state == _STATE_IDLE:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        if self.state == _STATE_CORRECT:
            self._pick_new_count()
        self.state = _STATE_IDLE

    def render(self, display):
        if self.state == _STATE_CORRECT:
            top_text, top_color, stick_color = "BRAVO !", C_TOP_CORRECT, C_STICK_CORRECT
        elif self.state == _STATE_WRONG:
            top_text, top_color, stick_color = "ESSAIE ENCORE", C_TOP_WRONG, C_STICK_WRONG
        else:
            top_text, top_color, stick_color = "COMPTE LES BATONS", C_TOP_IDLE, C_STICK

        display.text_centered("small", 7, top_color, top_text)

        # Sticks centered on the screen.
        total_w = self.count * STICK_W + (self.count - 1) * STICK_GAP
        start_x = (display.width - total_w) // 2
        for i in range(self.count):
            x = start_x + i * (STICK_W + STICK_GAP)
            display.rect(x, STICK_Y, STICK_W, STICK_H, stick_color)

        # Score bottom-right.
        score_txt = str(self.score)
        display.text("small",
                     display.width - len(score_txt) * 5 - 1, 31,
                     C_SCORE, score_txt)
