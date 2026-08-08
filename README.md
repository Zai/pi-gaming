# pi-gaming — Mini-jeux educatifs sur matrice LED

Plateforme de mini-jeux pour enfants (3-4 ans) affiches sur un bandeau LED
HUB75 pilote par un Raspberry Pi. Un clavier USB permet a l'enfant
d'interagir (apprentissage des lettres, des chiffres, des mots, calculs
simples...). Les jeux sont ajoutes en deposant un fichier dans `games/`.

## Contenu du dossier

```
pi-gaming/
├── main.py               Boucle principale, menu, chargement des jeux
├── engine.py             Display (matrice), Keyboard (evdev), classe Game
├── games/
│   ├── __init__.py       Registre : liste des jeux affiches au menu
│   └── hello.py          Jeu de demo (affiche la derniere touche pressee)
├── fonts/                Polices .bdf
├── config.example.json   Modele a copier en config.json
├── config.json           TA config (ignoree par git)
├── requirements.txt      Dependances Python
├── install.sh            Installation / mise a jour en une commande
└── README.md             Ce fichier
```

## Materiel

- Un Raspberry Pi (Zero 2 / 3 / 4 / 5) avec Raspberry Pi OS.
- **3 panneaux LED HUB75 64x32** chaines (192x32 total, comme le worldclock).
- Une carte **Adafruit RGB Matrix Bonnet / HAT**.
- Une **alimentation 5 V** dediee (~4 A max par panneau).
- **Un clavier USB** branche sur le Pi.

## Installation

```bash
cd ~/pi-gaming
cp config.example.json config.json   # premiere fois seulement
bash install.sh
```

Le script :
1. installe les dependances systeme (apt),
2. installe les paquets Python (`rgbmatrix` + `evdev`),
3. desactive le module son du Pi (conflit connu avec les LED),
4. ajoute l'utilisateur au groupe `input` (pour tester sans sudo),
5. cree un **service systemd** `pigaming`,
6. le demarre et l'active **au boot**.

Il est **idempotent** : relance-le apres chaque modif de code ou de config,
il ne casse rien.

## Ajouter un jeu

Un jeu = une classe qui herite de `engine.Game` :

```python
# games/my_game.py
from engine import Game

class MyGame(Game):
    name = "MON JEU"          # affiche au menu

    def on_key(self, event):  # une touche pressee (event.name, event.char)
        ...

    def tick(self, dt):       # mise a jour de l'etat (dt en secondes)
        ...

    def render(self, display):  # dessin sur le canvas
        display.text_centered("big", 20, (255, 200, 0), "COUCOU")
```

Puis dans `games/__init__.py` :

```python
from games.my_game import MyGame
GAMES = [HelloGame, MyGame]
```

Redemarre : `sudo systemctl restart pigaming`. Le jeu apparait au menu.

### API `display`

| Methode | Effet |
|---------|-------|
| `display.text(font, x, y, color, txt)` | Texte a la position (x, y). |
| `display.text_centered(font, y, color, txt, area_x=0, area_w=None)` | Texte centre dans une zone. |
| `display.pixel(x, y, color)` | Un pixel. |
| `display.rect(x, y, w, h, color)` | Rectangle plein. |
| `display.width`, `display.height` | Dimensions de la matrice. |

`font` = `"small"` (5x7), `"medium"` (6x10) ou `"big"` (7x13) par defaut
(cle du bloc `font` de la config). `color` = tuple `(R, G, B)` (0-255).

### API `event` (touche)

- `event.name` : nom evdev, `"KEY_A"`, `"KEY_LEFT"`, `"KEY_SPACE"`, `"KEY_ENTER"`, `"KEY_ESC"`...
- `event.char` : `"A"`, `"1"`, ... pour les touches alphanumeriques, `None` sinon.

`KEY_ESC` est intercepte par la boucle principale et renvoie au menu :
inutile de le gerer dans le jeu.

## Menu

- `←` / `→` (ou `A` / `D`) : changer de jeu.
- `Entree` (ou `Espace`) : lancer.
- `Echap` : quitter (dans un jeu = retour au menu ; dans le menu = arret).

## Configuration (`config.json`)

Meme principe que le worldclock : les defauts sont dans `main.py` (dict
`DEFAULTS`), `config.json` ne contient QUE ce qu'on veut surcharger
(deep-merge).

```json
{
  "panel": { "brightness": 60, "pixel_mapper_config": "Rotate:180" },
  "keyboard": { "device": "/dev/input/event3" },
  "fps": 60
}
```

### Bloc `panel`
Identique au worldclock : `rows`, `cols`, `chain_length`, `parallel`,
`gpio_slowdown`, `hardware_mapping`, `pixel_mapper_config`,
`disable_hardware_pulsing`, `brightness`.

### Bloc `keyboard`
- `device` : chemin absolu (`/dev/input/event3`) OU `null` pour
  l'auto-detection (choisit le premier device qui a KEY_A + KEY_Z + KEY_ENTER
  dans ses capacites).
- `layout` : `"qwerty"` (defaut) ou `"azerty"`. A mettre a `"azerty"` si
  le clavier physique est FR : la touche marquee "A" renverra bien `'A'`,
  "M" renverra `'M'`, etc. Les chiffres du haut restent des chiffres (pas
  besoin de Shift, mode "Azerty/Numerique").
  Note : evdev lit les keycodes **physiques** (independants du layout
  X/console). Ce reglage n'a donc rien a voir avec ce que dit `raspi-config`
  ou `setxkbmap` — il faut le mettre a `"azerty"` des que le clavier
  branche est un clavier FR, quel que soit le layout de l'OS.

  Ajouter un layout = ajouter une entree au dict `LAYOUTS` dans `engine.py`
  (mapping keycode evdev -> caractere visible).

### Aller plus loin : xkbcommon (non retenu ici)

Le remap manuel par dict marche tant qu'on ne vise que A-Z + 0-9. Pour
gerer proprement N'IMPORTE quel layout (dead keys `^` / `¨`, AltGr,
symboles, autres langues), la solution "propre" est
[`libxkbcommon`](https://xkbcommon.org/) — le moteur de layout utilise en
interne par X11 et Wayland — via son binding Python `python-xkbcommon` :

```python
# Esquisse — non implemente ici.
from xkbcommon import xkb
ctx = xkb.Context()
keymap = ctx.keymap_new_from_names(layout="fr", variant="azerty")
state = keymap.state_new()
# Dans le thread evdev : state.key_get_utf8(evdev_keycode + 8) -> str
```

Cout : une dep C (`libxkbcommon-dev` en apt) + une quinzaine de lignes
de wrap dans `engine.py`. A envisager le jour ou on veut des accents
francais, des mots avec ponctuation, ou plusieurs langues.

### Bloc `font`
`small` / `medium` / `big` : chemins vers des BDF **monospace** (la largeur
d'un glyph est deduite du nom : `5x7.bdf` -> 5 px).

## Gerer le service

```bash
sudo systemctl status pigaming     # etat
sudo systemctl restart pigaming    # relancer (apres modif config ou code)
sudo systemctl stop pigaming       # arreter
journalctl -u pigaming -f          # logs en direct
```

## Dev sans le service

Une fois `install.sh` passe (ajout au groupe `input`), et apres un logout/login :

```bash
sudo systemctl stop pigaming
sudo python3 main.py
```

(sudo car `rgbmatrix` a besoin des GPIO ; l'acces clavier passe par le
groupe input.)

## Depannage

- **Ecran noir / plantage** : `journalctl -u pigaming -f`. Essaie
  d'augmenter `gpio_slowdown`, ou passe `disable_hardware_pulsing` a `true`.
- **"Aucun clavier detecte"** : liste les devices avec
  `ls /dev/input/by-id/`, puis force `keyboard.device` dans `config.json`.
- **Les touches ne repondent pas mais le menu s'affiche** : le service
  n'a pas les droits sur `/dev/input`. Verifie qu'il tourne bien en `User=root`.
- **Couleurs fausses** : voir le README worldclock (probleme de mapping panneau).

## Desinstaller

```bash
sudo systemctl disable --now pigaming
sudo rm /etc/systemd/system/pigaming.service
sudo systemctl daemon-reload
```
