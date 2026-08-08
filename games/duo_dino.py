"""Co-op game: two dinos, one shared score.

The screen is split down the middle. Each half has its own dino running
against its own cactus stream:
- Left dino: LEFT SHIFT to jump.
- Right dino: RIGHT SHIFT to jump.

When a dino hits a cactus it flashes red for a moment and its own half
restarts — the other dino keeps running. Score = combined time survived
across both halves (grows twice as fast when both are alive), which nudges
the kids to help the other one instead of just focusing on their own dino.
"""
import random

from engine import Game
from games.dino import (
    CACT_H, CACT_W, CACTUS_SPRITE, CACT_TOP_Y,
    DEATH_HOLD_S, DINO_H, DINO_SPRITE, DINO_W,
    GROUND_Y,
    Cactus, Dino, rects_overlap,
    C_CACTUS, C_DINO, C_DINO_DEAD, C_DEATH, C_GROUND, C_SCORE,
    SCORE_PER_SECOND, SPAWN_MAX_S, SPAWN_MIN_S,
)


LEFT_KEY = "KEY_LEFTSHIFT"
RIGHT_KEY = "KEY_RIGHTSHIFT"

# Screen is 192 wide: two halves of 96, with dinos sitting near the left of
# each half so cacti have room to travel toward them.
HALF_WIDTH = 96
LEFT_DINO_X = 10
RIGHT_DINO_X = HALF_WIDTH + 10
LEFT_SPAWN_X = HALF_WIDTH - 4          # just off the right edge of the LEFT half
RIGHT_SPAWN_X = 2 * HALF_WIDTH - 4     # just off the right edge of the RIGHT half


class Lane:
    """One dino + one cactus stream on one half of the screen."""

    def __init__(self, dino_x, spawn_x, x_min):
        self.dino_x = dino_x
        self.spawn_x = spawn_x
        self.x_min = x_min                 # left edge of this lane
        self.dino = Dino(x=dino_x, base_y=GROUND_Y - DINO_H)
        self.cacti = []
        self.spawn_timer = SPAWN_MAX_S
        self.death_timer = 0.0

    @property
    def alive(self):
        return self.death_timer <= 0

    def jump(self):
        if self.alive:
            self.dino.jump()

    def tick(self, dt):
        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self._restart()
            return

        self.dino.tick(dt)
        for c in self.cacti:
            c.tick(dt)
        self.cacti = [c for c in self.cacti if c.x + CACT_W >= self.x_min]

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.cacti.append(Cactus(x=self.spawn_x))
            self.spawn_timer = random.uniform(SPAWN_MIN_S, SPAWN_MAX_S)

        if self._collides():
            self.death_timer = DEATH_HOLD_S

    def _collides(self):
        dy = int(self.dino.y)
        for c in self.cacti:
            if rects_overlap(self.dino.x, dy, DINO_W, DINO_H,
                             int(c.x), CACT_TOP_Y, CACT_W, CACT_H):
                return True
        return False

    def _restart(self):
        self.dino = Dino(x=self.dino_x, base_y=GROUND_Y - DINO_H)
        self.cacti = []
        self.spawn_timer = SPAWN_MAX_S

    def render(self, display):
        for c in self.cacti:
            display.sprite(CACTUS_SPRITE, int(c.x), CACT_TOP_Y, C_CACTUS)
        color = C_DINO_DEAD if not self.alive else C_DINO
        display.sprite(DINO_SPRITE, int(self.dino.x), int(self.dino.y), color)


class DuoDinoGame(Game):
    name = "DUO DINO"

    def __init__(self):
        self.left = Lane(dino_x=LEFT_DINO_X, spawn_x=LEFT_SPAWN_X, x_min=0)
        self.right = Lane(dino_x=RIGHT_DINO_X, spawn_x=RIGHT_SPAWN_X,
                          x_min=HALF_WIDTH)
        self.score_time = 0.0

    def on_key(self, event):
        if event.name == LEFT_KEY:
            self.left.jump()
        elif event.name == RIGHT_KEY:
            self.right.jump()

    def tick(self, dt):
        self.left.tick(dt)
        self.right.tick(dt)
        # Time counts once per living dino: with both alive, the score grows
        # twice as fast -> stronger incentive to keep each other alive.
        rate = int(self.left.alive) + int(self.right.alive)
        self.score_time += dt * rate

    def render(self, display):
        display.rect(0, GROUND_Y, display.width, 1, C_GROUND)
        # Faint vertical divider between the two halves.
        for y in range(0, 32, 2):
            display.pixel(HALF_WIDTH, y, (60, 60, 60))

        self.left.render(display)
        self.right.render(display)

        score_txt = str(int(self.score_time * SCORE_PER_SECOND))
        display.text_centered("small", 7, C_SCORE, score_txt)

        if not self.left.alive:
            display.text("small", 4, 7, C_DEATH, "AIE")
        if not self.right.alive:
            display.text("small", display.width - 20, 7, C_DEATH, "AIE")
