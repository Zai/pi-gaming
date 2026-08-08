"""Registry of games shown in the menu.

To add a game:
1. Create `games/my_game.py` with a class inheriting from `engine.Game`.
2. Import it here.
3. Append it to the `GAMES` list (menu order = list order).
"""
from games.hello import HelloGame
from games.find_key import FindKeyGame
from games.copy_word import CopyWordGame

GAMES = [
    HelloGame,
    FindKeyGame,
    CopyWordGame,
]
