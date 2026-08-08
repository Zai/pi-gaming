"""Registre des jeux disponibles au menu.

Pour ajouter un jeu :
1. Cree `games/mon_jeu.py` avec une classe qui herite de `engine.Game`.
2. Importe-la ici.
3. Ajoute-la a la liste `GAMES` (dans l'ordre d'affichage au menu).
"""
from games.hello import HelloGame

GAMES = [
    HelloGame,
]
