#!/usr/bin/env bash
#
# Installe (ou met a jour) le service pi-gaming. Idempotent :
# tu peux le relancer autant de fois que tu veux sans rien casser.
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pigaming"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
RUN_USER="${SUDO_USER:-$USER}"
PY="$(command -v python3)"

echo ">>> Projet : $PROJECT_DIR"

echo ">>> [1/6] Dependances systeme (recette upstream rgbmatrix)..."
# python3-pil (apt) est CRUCIAL : le paquet Debian place le header Imaging.h
# dans /usr/include/python3.X/, ou le shim C de rgbmatrix va le chercher.
# Une install de Pillow via pip ne suffit pas : la wheel place les headers
# dans site-packages/PIL/, endroit que CMake ne cherche pas.
sudo apt-get update -qq
sudo apt-get install -y \
  git \
  python-dev-is-python3 \
  python3-pil \
  python3-pip \
  cython3 >/dev/null

echo ">>> [2/6] Packages Python (rgbmatrix + evdev)..."
# --break-system-packages requis sur Raspberry Pi OS Bookworm+ (PEP 668).
sudo "$PY" -m pip install --break-system-packages -r "$PROJECT_DIR/requirements.txt"

echo ">>> [3/6] Desactivation du son integre (conflit connu avec rgbmatrix)..."
echo "blacklist snd_bcm2835" | sudo tee /etc/modprobe.d/blacklist-rgb-matrix.conf >/dev/null
sudo modprobe -r snd_bcm2835 2>/dev/null || true

echo ">>> [4/6] Acces /dev/input pour l'user ${RUN_USER}..."
# Le service tourne en root et lit /dev/input/event* sans probleme.
# Cet ajout permet de tester main.py directement en tant qu'user (dev sans sudo).
# Prise en compte apres un logout/login.
sudo usermod -aG input "$RUN_USER" || true

echo ">>> [5/6] Service systemd..."
sudo tee "$SERVICE_FILE" >/dev/null <<SERVICE
[Unit]
Description=pi-gaming - mini-jeux educatifs sur matrice LED
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PY $PROJECT_DIR/main.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
SERVICE

echo ">>> [6/6] Activation + demarrage..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME" >/dev/null
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo ">>> OK. pi-gaming tourne et redemarrera automatiquement au boot."
echo "    Etat  : sudo systemctl status $SERVICE_NAME"
echo "    Logs  : journalctl -u $SERVICE_NAME -f"
echo "    Config: $PROJECT_DIR/config.json  (puis: sudo systemctl restart $SERVICE_NAME)"
