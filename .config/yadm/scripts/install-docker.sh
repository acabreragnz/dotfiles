#!/bin/bash
# Instala Docker CE desde el repositorio oficial
# Referencia: https://docs.docker.com/engine/install/ubuntu/
set -e

if command -v docker >/dev/null 2>&1; then
  echo "[INFO] Docker ya está instalado: $(docker --version)"
  exit 0
fi

echo "[INFO] Instalando Docker CE..."

# Dependencias
sudo apt install -y ca-certificates curl

# GPG key y repo oficial
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Agregar usuario al grupo docker (sin sudo)
if ! groups "$USER" | grep -q docker; then
  sudo usermod -aG docker "$USER"
  echo "[INFO] Usuario agregado al grupo docker. Requiere nuevo login para aplicar."
fi

echo "[SUCCESS] Docker instalado: $(docker --version)"
