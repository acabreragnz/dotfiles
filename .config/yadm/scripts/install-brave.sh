#!/bin/bash
# Instala Brave Browser desde el repositorio oficial
# Referencia: https://brave.com/linux/
set -e

if command -v brave-browser >/dev/null 2>&1; then
  echo "[INFO] Brave ya está instalado: $(brave-browser --version)"
  exit 0
fi

echo "[INFO] Instalando Brave Browser..."

sudo curl -fsSLo /usr/share/keyrings/brave-browser-archive-keyring.gpg \
  https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main" | \
  sudo tee /etc/apt/sources.list.d/brave-browser-release.list > /dev/null

sudo apt update
sudo apt install -y brave-browser

echo "[SUCCESS] Brave instalado: $(brave-browser --version)"
