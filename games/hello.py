"""Minimal demo game: shows the last key pressed at the center of the screen.

Used to verify that the matrix, the keyboard and the render loop are wired
up correctly. Delete or replace it once a real game exists.
"""
from engine import Game


class HelloGame(Game):
    name = "BONJOUR"

    def __init__(self):
        self.last = "?"

    def on_key(self, event):
        if event.char is not None:
            self.last = event.char.upper()
        else:
            # Special key: show its short name (SPACE, LEFT, ENTER...).
            self.last = event.name.replace("KEY_", "")[:6]

    def render(self, display):
        display.text_centered("small", 9, (0, 200, 255), "TAPE UNE TOUCHE")
        display.text_centered("big", 25, (255, 200, 0), self.last)
