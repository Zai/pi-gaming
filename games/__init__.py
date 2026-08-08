"""Registry of games shown in the menu.

To add a game:
1. Create `games/my_game.py` with a class inheriting from `engine.Game`.
2. Import it here.
3. Append it to the `GAMES` list (menu order = list order).
"""
from games.hello import HelloGame
from games.find_key import FindKeyGame
from games.copy_word import CopyWordGame
from games.dino import DinoGame
from games.bridge import BridgeGame
from games.boat import BoatGame
from games.basket import BasketGame
from games.duo_dino import DuoDinoGame

GAMES = [
    HelloGame,
    FindKeyGame,
    CopyWordGame,
    DinoGame,
    BridgeGame,
    BoatGame,
    BasketGame,
    DuoDinoGame,
]
