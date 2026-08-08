"""Jeu de demo minimal : affiche la derniere touche pressee au centre.

Sert a valider que la matrice, le clavier et la boucle de rendu marchent.
Se remplace ou se supprime des qu'un vrai jeu existe.
"""
from engine import Game


class HelloGame(Game):
    name = "HELLO"

    def __init__(self):
        self.last = "?"

    def on_key(self, event):
        if event.char is not None:
            self.last = event.char.upper()
        else:
            # Touche speciale : on affiche son nom court (SPACE, LEFT, ENTER...).
            self.last = event.name.replace("KEY_", "")[:6]

    def render(self, display):
        display.text_centered("small", 9, (0, 200, 255), "TAPE UNE TOUCHE")
        display.text_centered("big", 25, (255, 200, 0), self.last)
