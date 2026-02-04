#!/bin/bash
# Script de Hardening de Seguridad
# Cumplimiento con políticas de seguridad corporativas (Rabbet)
# Ejecutable: Puede correr con o sin sudo (detecta automáticamente)

set -e

SCRIPT_NAME="Security Hardening"
COLOR_GREEN="\033[0;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[0;31m"
COLOR_BLUE="\033[0;34m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_BLUE}=========================================="
echo -e "${SCRIPT_NAME}"
echo -e "==========================================${COLOR_RESET}"
echo ""

# ==========================================
# 1. Configurar Screen Lock (No requiere sudo)
# ==========================================
echo -e "${COLOR_BLUE}[1/4] Configurando screen lock automático...${COLOR_RESET}"

if command -v gsettings &> /dev/null; then
    # Auto-lock después de 5 minutos (300 segundos)
    gsettings set org.gnome.desktop.screensaver lock-delay 300
    gsettings set org.gnome.desktop.screensaver idle-activation-enabled true
    gsettings set org.gnome.desktop.screensaver lock-enabled true
    gsettings set org.gnome.desktop.session idle-delay 300

    echo -e "${COLOR_GREEN}✅ Screen lock configurado (5 minutos)${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠️  gsettings no disponible (no es GNOME)${COLOR_RESET}"
fi

echo ""

# ==========================================
# 2. Verificar Actualizaciones Automáticas
# ==========================================
echo -e "${COLOR_BLUE}[2/4] Verificando actualizaciones automáticas...${COLOR_RESET}"

if systemctl is-active --quiet unattended-upgrades.service; then
    echo -e "${COLOR_GREEN}✅ unattended-upgrades activo${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠️  unattended-upgrades no está activo${COLOR_RESET}"
    if [ "$EUID" -eq 0 ]; then
        echo "   Intentando habilitar..."
        systemctl enable --now unattended-upgrades.service
        echo -e "${COLOR_GREEN}✅ unattended-upgrades habilitado${COLOR_RESET}"
    else
        echo "   Ejecuta con sudo para habilitar automáticamente"
    fi
fi

echo ""

# ==========================================
# 3. Configurar Política de Contraseñas (Requiere sudo)
# ==========================================
echo -e "${COLOR_BLUE}[3/4] Configurando política de contraseñas...${COLOR_RESET}"

PWQUALITY_CONF="/etc/security/pwquality.conf"

if [ "$EUID" -ne 0 ]; then
    echo -e "${COLOR_YELLOW}⚠️  Se requiere sudo para configurar política de contraseñas${COLOR_RESET}"
    echo "   Ejecuta: sudo $0"
else
    # Verificar si ya está configurado
    if grep -q "Rabbet Security Policy" "$PWQUALITY_CONF" 2>/dev/null; then
        echo -e "${COLOR_GREEN}✅ Política de contraseñas ya configurada${COLOR_RESET}"
    else
        # Crear backup
        BACKUP_FILE="${PWQUALITY_CONF}.backup-$(date +%Y%m%d-%H%M%S)"
        cp "$PWQUALITY_CONF" "$BACKUP_FILE"

        # Agregar configuración
        cat >> "$PWQUALITY_CONF" << 'EOF'

# ==========================================
# Rabbet Security Policy
# ==========================================
minlen = 14
dcredit = -1
ucredit = -1
lcredit = -1
ocredit = -1
maxrepeat = 3
dictcheck = 1
usercheck = 1
enforce_for_root
EOF

        echo -e "${COLOR_GREEN}✅ Política de contraseñas configurada (backup: $BACKUP_FILE)${COLOR_RESET}"
    fi
fi

echo ""

# ==========================================
# 4. Verificar Firewall (UFW)
# ==========================================
echo -e "${COLOR_BLUE}[4/4] Verificando firewall...${COLOR_RESET}"

if command -v ufw &> /dev/null; then
    if [ "$EUID" -eq 0 ]; then
        UFW_STATUS=$(ufw status | head -1)
        if echo "$UFW_STATUS" | grep -q "inactive"; then
            echo -e "${COLOR_YELLOW}⚠️  UFW está inactivo${COLOR_RESET}"
            echo "   Considera ejecutar:"
            echo "   sudo ufw enable"
            echo "   sudo ufw default deny incoming"
            echo "   sudo ufw default allow outgoing"
        else
            echo -e "${COLOR_GREEN}✅ UFW activo${COLOR_RESET}"
        fi
    else
        echo -e "${COLOR_YELLOW}⚠️  Se requiere sudo para verificar UFW${COLOR_RESET}"
    fi
else
    echo -e "${COLOR_YELLOW}⚠️  UFW no instalado${COLOR_RESET}"
    if [ "$EUID" -eq 0 ]; then
        echo "   Instalando UFW..."
        apt install -y ufw
    else
        echo "   Ejecuta: sudo apt install ufw"
    fi
fi

echo ""

# ==========================================
# Resumen
# ==========================================
echo -e "${COLOR_BLUE}==========================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}✅ Hardening de Seguridad Completado${COLOR_RESET}"
echo -e "${COLOR_BLUE}==========================================${COLOR_RESET}"
echo ""
echo "Configuraciones aplicadas:"
echo "  • Screen lock: 5 minutos"
echo "  • Actualizaciones automáticas: verificadas"
echo "  • Política de contraseñas: 14+ caracteres"
echo "  • Firewall: verificado"
echo ""
echo -e "${COLOR_YELLOW}Nota: Algunas configuraciones requieren sudo.${COLOR_RESET}"
echo -e "${COLOR_YELLOW}Ejecuta con: sudo bash $0${COLOR_RESET}"
echo ""
