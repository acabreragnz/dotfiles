#!/bin/bash
# Configuraciones de seguridad de GNOME/gsettings
# Solo screen lock - para ser ejecutado desde bootstrap

# Screen lock automático (5 minutos)
gsettings set org.gnome.desktop.screensaver lock-delay 300
gsettings set org.gnome.desktop.screensaver idle-activation-enabled true
gsettings set org.gnome.desktop.screensaver lock-enabled true
gsettings set org.gnome.desktop.session idle-delay 300

echo "✅ Configuraciones de seguridad GNOME aplicadas"
