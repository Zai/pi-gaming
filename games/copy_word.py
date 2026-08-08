"""Game: copy words.

Show a word picked from a small vocabulary of common french words split
into categories (fruits, vegetables, animals, sports, objects, colors,
body parts, family, nature). The child types the letters one by one.

- Already-typed letters glow green.
- The next expected letter is highlighted in yellow.
- Untyped letters stay dim gray.
- A wrong key briefly flashes the pending letter red; progress is NEVER
  reset (young children need forgiving feedback).
- Once the word is complete, "BRAVO !" for a moment, then a new word.

Words are stored without accents on purpose: our AZERTY remap produces bare
letters (KEY_E -> 'E'), and typing accented forms would need Shift/AltGr
combos that a 3-year-old cannot manage.
"""
import random

from engine import Game


WORDS = {
    "FRUITS": [
        "POMME", "POIRE", "KIWI", "PRUNE", "FRAISE", "BANANE",
        "ORANGE", "RAISIN", "CITRON", "CERISE", "MELON", "ANANAS",
    ],
    "LEGUMES": [
        "TOMATE", "PATATE", "CAROTTE", "SALADE", "RADIS", "CHOU",
        "POIS", "MAIS", "NAVET", "OIGNON", "POIREAU",
    ],
    "ANIMAUX": [
        "CHAT", "CHIEN", "VACHE", "LAPIN", "POULE", "CANARD",
        "LION", "TIGRE", "OURS", "LOUP", "SINGE", "ZEBRE",
        "PANDA", "GIRAFE", "MOUTON", "POISSON", "TORTUE", "SERPENT",
    ],
    "SPORTS": [
        "FOOT", "TENNIS", "JUDO", "DANSE", "VELO", "GYM",
        "YOGA", "BOXE", "SKI", "GOLF", "RUGBY", "KARATE", "SURF",
    ],
    "OBJETS": [
        "LIVRE", "STYLO", "TABLE", "CHAISE", "LAMPE", "LIT",
        "BOL", "TASSE", "JOUET", "VOITURE", "AVION", "TRAIN",
        "BATEAU", "BALLON", "POUPEE",
    ],
    "COULEURS": [
        "ROUGE", "BLEU", "VERT", "JAUNE", "ROSE", "NOIR",
        "BLANC", "VIOLET", "ORANGE", "GRIS", "MARRON",
    ],
    "CORPS": [
        "MAIN", "PIED", "TETE", "DENT", "DOIGT", "BRAS",
        "JAMBE", "DOS", "NEZ", "OEIL", "BOUCHE", "VENTRE",
    ],
    "FAMILLE": [
        "PAPA", "MAMAN", "BEBE", "MAMIE", "PAPI",
        "FRERE", "SOEUR", "ONCLE", "TANTE",
    ],
    "NATURE": [
        "SOLEIL", "LUNE", "ETOILE", "ARBRE", "FLEUR", "HERBE",
        "PLUIE", "NEIGE", "VENT", "MER", "MONTAGNE",
    ],
}

_COLOR_TYPED = (0, 255, 100)
_COLOR_NEXT = (255, 200, 0)
_COLOR_PENDING = (90, 90, 90)
_COLOR_WRONG = (255, 60, 60)
_COLOR_CATEGORY = (0, 200, 255)
_COLOR_SCORE = (120, 120, 120)

_COMPLETE_HOLD_S = 1.0
_WRONG_FLASH_S = 0.25


class CopyWordGame(Game):
    name = "MOTS"

    def __init__(self):
        self.score = 0
        self.category = None
        self.word = None
        self.typed = 0
        self.complete_timer = 0.0
        self.wrong_flash_timer = 0.0
        self._pick_word()

    def _pick_word(self):
        category = random.choice(list(WORDS))
        # Avoid repeating the same word back-to-back.
        pool = WORDS[category]
        if self.word is not None and len(pool) > 1:
            pool = [w for w in pool if w != self.word]
        self.category = category
        self.word = random.choice(pool)
        self.typed = 0

    def on_key(self, event):
        # During the celebration or on non-letter keys: ignore.
        if self.complete_timer > 0 or event.char is None:
            return
        expected = self.word[self.typed]
        if event.char.upper() == expected:
            self.typed += 1
            if self.typed == len(self.word):
                self.score += 1
                self.complete_timer = _COMPLETE_HOLD_S
        else:
            self.wrong_flash_timer = _WRONG_FLASH_S

    def tick(self, dt):
        if self.wrong_flash_timer > 0:
            self.wrong_flash_timer = max(0.0, self.wrong_flash_timer - dt)
        if self.complete_timer > 0:
            self.complete_timer -= dt
            if self.complete_timer <= 0:
                self._pick_word()

    def render(self, display):
        # Top: category name (or "BRAVO !" during the celebration).
        if self.complete_timer > 0:
            display.text_centered("small", 7, _COLOR_TYPED, "BRAVO !")
        else:
            display.text_centered("small", 7, _COLOR_CATEGORY, self.category)

        # Middle: the word, colored per-letter.
        self._draw_word(display, y=22)

        # Bottom-right: score.
        score_txt = str(self.score)
        display.text("small",
                     display.width - len(score_txt) * 5 - 1, 31,
                     _COLOR_SCORE, score_txt)

    def _draw_word(self, display, y):
        cw = display.char_widths["big"]
        total_w = len(self.word) * cw
        start_x = (display.width - total_w) // 2
        for i, ch in enumerate(self.word):
            display.text("big", start_x + i * cw, y, self._letter_color(i), ch)

    def _letter_color(self, i):
        if self.complete_timer > 0:
            return _COLOR_TYPED
        if i < self.typed:
            return _COLOR_TYPED
        if i == self.typed:
            return _COLOR_WRONG if self.wrong_flash_timer > 0 else _COLOR_NEXT
        return _COLOR_PENDING
