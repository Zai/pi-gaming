"""Game: dino runner.

A small character runs on the ground; cactus obstacles scroll from right
to left. Press SPACE to jump over them. Single-key coordination trainer.

On collision: brief "AIE !" flash, then everything resets and running
resumes automatically. No hard game-over screen — young children need
continuous flow, not a state that requires them to know how to restart.
"""
import random

from engine import Game


# --- Layout (32-tall screen: rows 0..31) ------------------------------------

GROUND_Y = 28              # y of the 1-pixel ground line

# --- Sprites (# = lit pixel) ------------------------------------------------

DINO_SPRITE = [
    "..####",
    "..####",
    "..#.##",     # eye
    "..####",
    "#.####",     # front arm
    "######",
    ".####.",
    ".####.",
    ".#..#.",     # legs
    ".#..#.",
]

CACTUS_SPRITE = [
    "#.#",
    "#.#",
    "###",
    ".#.",
    ".#.",
    ".#.",
    ".#.",
]

DINO_W, DINO_H = len(DINO_SPRITE[0]), len(DINO_SPRITE)
CACT_W, CACT_H = len(CACTUS_SPRITE[0]), len(CACTUS_SPRITE)

DINO_X = 15                # dino's fixed horizontal position
DINO_BASE_Y = GROUND_Y - DINO_H
CACT_TOP_Y = GROUND_Y - CACT_H

# --- Physics ----------------------------------------------------------------

JUMP_V = -140.0            # initial jump velocity, px/s (up is negative)
GRAVITY = 600.0            # px/s^2. Peak = v^2/(2g) ~16 px, air ~0.47 s.

# --- Obstacles --------------------------------------------------------------

SPEED = 60.0               # constant scroll speed, px/s
SPAWN_MIN_S = 1.6
SPAWN_MAX_S = 2.8
SPAWN_X = 195              # just off the right edge of a 192-wide screen

# --- Scoring / death --------------------------------------------------------

SCORE_PER_SECOND = 5
DEATH_HOLD_S = 0.9

# --- Colors -----------------------------------------------------------------

C_GROUND = (100, 100, 100)
C_DINO = (255, 220, 0)
C_DINO_DEAD = (255, 60, 60)
C_CACTUS = (0, 220, 120)
C_SCORE = (120, 120, 120)
C_DEATH = (255, 80, 80)


class Dino:
    """Jumper physics. Parameterized so DUO DINO can reuse it."""

    def __init__(self, x, base_y):
        self.x = x
        self.base_y = base_y
        self.reset()

    def reset(self):
        self.y = float(self.base_y)
        self.vy = 0.0
        self.on_ground = True

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_V
            self.on_ground = False

    def tick(self, dt):
        if self.on_ground:
            return
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        if self.y >= self.base_y:
            self.y = float(self.base_y)
            self.vy = 0.0
            self.on_ground = True


class Cactus:
    def __init__(self, x):
        self.x = float(x)

    def tick(self, dt, speed=SPEED):
        self.x -= speed * dt

    @property
    def off_screen(self):
        return self.x + CACT_W < 0


def rects_overlap(ax, ay, aw, ah, bx, by, bw, bh):
    return not (ax + aw <= bx or bx + bw <= ax
                or ay + ah <= by or by + bh <= ay)


class DinoGame(Game):
    name = "DINO"

    def __init__(self):
        self.dino = Dino(x=DINO_X, base_y=DINO_BASE_Y)
        self.cacti = []
        self.spawn_timer = SPAWN_MAX_S
        self.score_time = 0.0
        self.death_timer = 0.0

    # ---- input ------------------------------------------------------------

    def on_key(self, event):
        if event.name != "KEY_SPACE" or self.death_timer > 0:
            return
        self.dino.jump()

    # ---- update -----------------------------------------------------------

    def tick(self, dt):
        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self._restart()
            return

        self.score_time += dt
        self.dino.tick(dt)

        for c in self.cacti:
            c.tick(dt)
        self.cacti = [c for c in self.cacti if not c.off_screen]

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.cacti.append(Cactus(x=SPAWN_X))
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
        self.dino = Dino(x=DINO_X, base_y=DINO_BASE_Y)
        self.cacti = []
        self.spawn_timer = SPAWN_MAX_S
        self.score_time = 0.0

    # ---- render -----------------------------------------------------------

    def render(self, display):
        display.rect(0, GROUND_Y, display.width, 1, C_GROUND)

        for c in self.cacti:
            display.sprite(CACTUS_SPRITE, int(c.x), CACT_TOP_Y, C_CACTUS)

        dino_color = C_DINO_DEAD if self.death_timer > 0 else C_DINO
        display.sprite(DINO_SPRITE, int(self.dino.x), int(self.dino.y),
                       dino_color)

        score_txt = str(int(self.score_time * SCORE_PER_SECOND))
        display.text("small",
                     display.width - len(score_txt) * 5 - 1, 7,
                     C_SCORE, score_txt)

        if self.death_timer > 0:
            display.text("small", 2, 7, C_DEATH, "AIE !")
