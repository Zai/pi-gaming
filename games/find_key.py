"""Game: find the key.

A random target (A-Z or 0-9) is displayed. The child presses the matching
key. Green flash + "BRAVO !" on hit, soft red flash on miss (the target
stays so the child can retry).

Non-alphanumeric keys (arrows, modifiers, ...) are ignored, not counted
as attempts.
"""
import random

from engine import Game


TARGETS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

_STATE_IDLE = "idle"
_STATE_CORRECT = "correct"
_STATE_WRONG = "wrong"

_CORRECT_HOLD_S = 0.7
_WRONG_HOLD_S = 0.3


class FindKeyGame(Game):
    name = "TROUVE"

    def __init__(self):
        self.target = random.choice(TARGETS)
        self.state = _STATE_IDLE
        self.timer = 0.0
        self.score = 0

    def _pick_new_target(self):
        # Avoid repeating the same target back-to-back.
        pool = [c for c in TARGETS if c != self.target]
        self.target = random.choice(pool)

    def on_key(self, event):
        if self.state != _STATE_IDLE or event.char is None:
            return
        if event.char.upper() == self.target:
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
            self._pick_new_target()
        self.state = _STATE_IDLE

    def render(self, display):
        if self.state == _STATE_CORRECT:
            top_color = target_color = (0, 255, 100)
            top_text = "BRAVO !"
        elif self.state == _STATE_WRONG:
            top_color = target_color = (255, 100, 100)
            top_text = "ESSAIE ENCORE"
        else:
            top_color = (0, 200, 255)
            target_color = (255, 200, 0)
            top_text = "TROUVE LA TOUCHE"

        display.text_centered("small", 8, top_color, top_text)
        # Repeat the target three times across the 192 px screen so it
        # feels big even with a 7-wide font.
        panel_w = display.width // 3
        for i in range(3):
            display.text_centered("big", 26, target_color,
                                  self.target,
                                  area_x=i * panel_w, area_w=panel_w)
        # Small score in the bottom-right corner.
        score_txt = str(self.score)
        display.text("small",
                     display.width - len(score_txt) * 5 - 1, 31,
                     (120, 120, 120), score_txt)
