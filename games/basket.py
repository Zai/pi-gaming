"""Co-op game: catch the falling fruit with two baskets.

Two baskets side by side at the bottom of the screen. Fruits fall from
random positions above. Each kid steers one basket:
- Left kid: A (physical top-left home row) to go left, D to go right.
- Right kid: LEFT / RIGHT arrows.

Baskets are held in place (movement while the key is held). Caught fruit
= +1 to the shared score. Missed fruit = no penalty (young children need
forgiving rules).
"""
import random

from engine import Game


LEFT_LEFT_KEY = "KEY_A"
LEFT_RIGHT_KEY = "KEY_D"
RIGHT_LEFT_KEY = "KEY_LEFT"
RIGHT_RIGHT_KEY = "KEY_RIGHT"

BASKET_W = 11
BASKET_H = 4
BASKET_Y = 27              # top of the basket
BASKET_SPEED = 55.0        # pixels per second

FRUIT_SIZE = 2
FRUIT_FALL_SPEED = 22.0
FRUIT_SPAWN_MIN_S = 0.6
FRUIT_SPAWN_MAX_S = 1.4

LEFT_ZONE = (0, 95)        # inclusive-exclusive x range for left basket
RIGHT_ZONE = (96, 192)

BASKET_SPRITE = [
    "#.........#",
    "#.........#",
    "#.........#",
    "###########",
]

FRUIT_COLORS = [
    (255, 60, 60),    # red
    (255, 160, 0),    # orange
    (255, 220, 0),    # yellow
    (100, 230, 100),  # green
    (200, 120, 255),  # purple
]

C_BASKET = (200, 140, 60)
C_LABEL = (120, 120, 120)
C_SCORE = (0, 220, 120)


class Basket:
    def __init__(self, zone, left_key, right_key):
        self.zone_min, self.zone_max = zone
        self.left_key = left_key
        self.right_key = right_key
        self.x = float((self.zone_min + self.zone_max) / 2 - BASKET_W / 2)

    def tick(self, dt, keyboard):
        if keyboard is None:
            return
        if keyboard.is_held(self.left_key):
            self.x -= BASKET_SPEED * dt
        if keyboard.is_held(self.right_key):
            self.x += BASKET_SPEED * dt
        # Clamp to the basket's own half of the screen.
        self.x = max(float(self.zone_min),
                     min(float(self.zone_max - BASKET_W), self.x))

    def catches(self, fruit_x, fruit_y):
        # Fruit is caught when its center overlaps the basket's opening.
        if fruit_y + FRUIT_SIZE < BASKET_Y:
            return False
        if fruit_y > BASKET_Y + BASKET_H:
            return False
        return int(self.x) <= fruit_x < int(self.x) + BASKET_W


class Fruit:
    def __init__(self, x, color):
        self.x = x
        self.y = 0.0
        self.color = color

    def tick(self, dt):
        self.y += FRUIT_FALL_SPEED * dt


class BasketGame(Game):
    name = "PANIER"

    def __init__(self):
        self.left_basket = Basket(LEFT_ZONE, LEFT_LEFT_KEY, LEFT_RIGHT_KEY)
        self.right_basket = Basket(RIGHT_ZONE, RIGHT_LEFT_KEY, RIGHT_RIGHT_KEY)
        self.fruits = []
        self.spawn_timer = FRUIT_SPAWN_MIN_S
        self.score = 0

    def tick(self, dt):
        self.left_basket.tick(dt, self.keyboard)
        self.right_basket.tick(dt, self.keyboard)

        for f in self.fruits:
            f.tick(dt)

        surviving = []
        for f in self.fruits:
            caught = (self.left_basket.catches(f.x, f.y)
                      or self.right_basket.catches(f.x, f.y))
            if caught:
                self.score += 1
                continue
            if f.y >= 32:
                continue  # dropped off the bottom, no penalty
            surviving.append(f)
        self.fruits = surviving

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn_fruit()
            self.spawn_timer = random.uniform(FRUIT_SPAWN_MIN_S,
                                              FRUIT_SPAWN_MAX_S)

    def _spawn_fruit(self):
        x = random.randint(2, 189)
        color = random.choice(FRUIT_COLORS)
        self.fruits.append(Fruit(x, color))

    def render(self, display):
        # Baskets.
        display.sprite(BASKET_SPRITE, int(self.left_basket.x), BASKET_Y,
                       C_BASKET)
        display.sprite(BASKET_SPRITE, int(self.right_basket.x), BASKET_Y,
                       C_BASKET)

        # Fruits (2x2 blocks so they're visible enough).
        for f in self.fruits:
            display.rect(f.x, int(f.y), FRUIT_SIZE, FRUIT_SIZE, f.color)

        # Score in the top-middle.
        score_txt = str(self.score)
        display.text_centered("small", 7, C_SCORE, score_txt)

        # Discreet key hints on either side.
        display.text("small", 2, 7, C_LABEL, "A D")
        display.text("small", display.width - 18, 7, C_LABEL, "< >")
