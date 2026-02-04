#!/bin/bash
# Script para configurar autenticación por huella dactilar
# Uso: ./setup-fingerprint-auth.sh [opciones]
#
# Opciones:
#   --skip-enroll       Saltar el registro de huellas si ya existen
#   --skip-verify       Saltar la prueba de verificación
#   --force             Forzar re-registro de huellas
#   --help              Mostrar esta ayuda

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables de configuración
SKIP_ENROLL=false
SKIP_VERIFY=false
FORCE_ENROLL=false

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-enroll)
            SKIP_ENROLL=true
            shift
            ;;
        --skip-verify)
            SKIP_VERIFY=true
            shift
            ;;
        --force)
            FORCE_ENROLL=true
            shift
            ;;
        --help)
            echo "Uso: $0 [opciones]"
            echo ""
            echo "Opciones:"
            echo "  --skip-enroll    Saltar el registro de huellas si ya existen"
            echo "  --skip-verify    Saltar la prueba de verificación"
            echo "  --force          Forzar re-registro de huellas"
            echo "  --help           Mostrar esta ayuda"
            exit 0
            ;;
        *)
            echo -e "${RED}Error:${NC} Opción desconocida: $1"
            echo "Usa --help para ver las opciones disponibles"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Configuración de Autenticación por Huella Dactilar  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Obtener el usuario real (no root si se ejecuta con sudo)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
else
    REAL_USER="$USER"
fi

echo -e "${YELLOW}Usuario a configurar:${NC} $REAL_USER"
echo ""

# Verificar hardware
echo -e "${YELLOW}[1/5]${NC} Verificando hardware de huella dactilar..."
if lsusb | grep -i fingerprint > /dev/null 2>&1; then
    FINGERPRINT_DEVICE=$(lsusb | grep -i fingerprint)
    echo -e "${GREEN}✓${NC} Dispositivo encontrado:"
    echo "  $FINGERPRINT_DEVICE"
else
    echo -e "${YELLOW}⚠${NC}  No se detectó lector de huellas dactilares"
    echo -e "${BLUE}ℹ${NC}  Este script requiere hardware de huella dactilar"
    echo -e "${BLUE}ℹ${NC}  Saltando configuración..."
    exit 0
fi
echo ""

# Verificar software
echo -e "${YELLOW}[2/5]${NC} Verificando software fprintd..."
if command -v fprintd-enroll &> /dev/null; then
    echo -e "${GREEN}✓${NC} fprintd está instalado"
else
    echo -e "${RED}✗${NC} fprintd no está instalado"
    echo "Instalando fprintd..."
    sudo apt update && sudo apt install -y fprintd libpam-fprintd
fi
echo ""

# Habilitar fprintd en PAM
echo -e "${YELLOW}[3/5]${NC} Configurando PAM para usar huella dactilar..."
echo -e "${BLUE}ℹ${NC}  Esto habilitará la autenticación por huella para sudo, login, etc."

# Verificar si ya está habilitado
if grep -q "pam_fprintd.so" /etc/pam.d/common-auth 2>/dev/null; then
    echo -e "${GREEN}✓${NC} fprintd ya está configurado en PAM"
else
    echo -e "${YELLOW}→${NC} Habilitando fprintd en PAM..."
    # Usar pam-auth-update para habilitar fprintd de forma segura
    sudo pam-auth-update --package --enable fprintd
    echo -e "${GREEN}✓${NC} fprintd habilitado en PAM"
fi

# Configurar reintentos de huella (max-tries)
echo -e "${YELLOW}→${NC} Configurando reintentos de huella (max-tries=5)..."
PAM_FILE="/etc/pam.d/common-auth"
if [ -f "$PAM_FILE" ] && grep -q "pam_fprintd.so" "$PAM_FILE"; then
    # Crear backup con timestamp
    BACKUP_FILE="${PAM_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    sudo cp "$PAM_FILE" "$BACKUP_FILE"

    # Si ya tiene max-tries, actualizarlo; si no, agregarlo
    if grep -q "pam_fprintd.so.*max-tries=" "$PAM_FILE"; then
        sudo sed -i 's/pam_fprintd\.so\(.*\)max-tries=[0-9]\+/pam_fprintd.so\1max-tries=5/' "$PAM_FILE"
    else
        sudo sed -i 's/pam_fprintd\.so/pam_fprintd.so max-tries=5/' "$PAM_FILE"
    fi

    # Verificar el cambio
    if grep -q "pam_fprintd.so.*max-tries=5" "$PAM_FILE"; then
        echo -e "${GREEN}✓${NC} Configurados 5 intentos de huella"
    else
        echo -e "${YELLOW}⚠${NC} No se pudo configurar max-tries"
    fi
else
    echo -e "${YELLOW}⚠${NC} PAM no está configurado para huella digital"
fi
echo ""

# Gestión de huellas dactilares
echo -e "${YELLOW}[4/5]${NC} Gestión de huellas dactilares..."

# Verificar si ya tiene huellas registradas
HAS_FINGERPRINTS=false
FINGERPRINT_COUNT=0
if sudo fprintd-list "$REAL_USER" 2>/dev/null | grep -q "enrolled"; then
    HAS_FINGERPRINTS=true
    FINGERPRINT_COUNT=$(sudo fprintd-list "$REAL_USER" 2>/dev/null | grep -c "finger:" || echo 0)
fi

# Determinar acción basada en flags o preguntar al usuario
SKIP_ENROLL_SECTION=false
DELETE_EXISTING=false

if [ "$HAS_FINGERPRINTS" = true ]; then
    # Ya tiene huellas registradas
    echo -e "${GREEN}✓${NC} Ya tienes ${GREEN}${FINGERPRINT_COUNT}${NC} huella(s) registrada(s)"

    if [ "$SKIP_ENROLL" = true ]; then
        echo -e "${BLUE}ℹ${NC}  Saltando registro (--skip-enroll)"
        SKIP_ENROLL_SECTION=true
    elif [ "$FORCE_ENROLL" = true ]; then
        echo -e "${YELLOW}→${NC} Eliminando huellas existentes (--force)..."
        sudo fprintd-delete "$REAL_USER" 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Huellas eliminadas"
        SKIP_ENROLL_SECTION=false
        DELETE_EXISTING=true
    else
        # Modo interactivo: dar opciones
        echo ""
        echo "¿Qué quieres hacer?"
        echo "  1) Mantener las huellas existentes (no hacer nada)"
        echo "  2) Registrar una huella adicional"
        echo "  3) Eliminar todas y registrar nuevas"
        read -p "Selecciona (1-3) [1]: " fingerprint_action

        case ${fingerprint_action:-1} in
            1)
                echo -e "${BLUE}ℹ${NC}  Manteniendo huellas existentes"
                SKIP_ENROLL_SECTION=true
                ;;
            2)
                echo -e "${YELLOW}→${NC} Preparando para registrar huella adicional..."
                SKIP_ENROLL_SECTION=false
                DELETE_EXISTING=false
                ;;
            3)
                echo -e "${YELLOW}→${NC} Eliminando todas las huellas..."
                sudo fprintd-delete "$REAL_USER" 2>/dev/null || true
                echo -e "${GREEN}✓${NC} Huellas eliminadas"
                SKIP_ENROLL_SECTION=false
                DELETE_EXISTING=true
                ;;
            *)
                echo -e "${BLUE}ℹ${NC}  Manteniendo huellas existentes (opción no válida)"
                SKIP_ENROLL_SECTION=true
                ;;
        esac
    fi
else
    # No tiene huellas registradas
    echo -e "${BLUE}ℹ${NC}  No tienes huellas registradas"

    if [ "$SKIP_ENROLL" = true ]; then
        echo -e "${BLUE}ℹ${NC}  Saltando registro (--skip-enroll)"
        SKIP_ENROLL_SECTION=true
    else
        # Preguntar si quiere registrar
        read -p "¿Quieres registrar una huella ahora? (S/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo -e "${BLUE}ℹ${NC}  Saltando registro de huella"
            SKIP_ENROLL_SECTION=true
        else
            echo -e "${YELLOW}→${NC} Preparando para registrar huella..."
            SKIP_ENROLL_SECTION=false
        fi
    fi
fi
echo ""

# Registrar huellas
if [ "$SKIP_ENROLL_SECTION" = false ]; then
    echo -e "${YELLOW}[5/5]${NC} Registrando huellas dactilares..."
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  INSTRUCCIONES:                                       ║${NC}"
    echo -e "${BLUE}║  1. Coloca tu dedo en el lector cuando se te indique ║${NC}"
    echo -e "${BLUE}║  2. Levanta y vuelve a colocar el dedo varias veces  ║${NC}"
    echo -e "${BLUE}║  3. Cubre diferentes áreas de tu huella              ║${NC}"
    echo -e "${BLUE}║  4. El proceso requiere ~5 lecturas exitosas         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Preguntar qué dedo registrar
    echo "¿Qué dedo quieres registrar?"
    echo "  1) Dedo índice derecho (recomendado)"
    echo "  2) Dedo índice izquierdo"
    echo "  3) Pulgar derecho"
    echo "  4) Pulgar izquierdo"
    echo "  5) Otro dedo"
    read -p "Selecciona (1-5): " finger_choice

    case $finger_choice in
        1) FINGER="right-index-finger" ;;
        2) FINGER="left-index-finger" ;;
        3) FINGER="right-thumb" ;;
        4) FINGER="left-thumb" ;;
        5)
            echo "Dedos disponibles:"
            echo "  right-thumb, right-index-finger, right-middle-finger,"
            echo "  right-ring-finger, right-little-finger"
            echo "  left-thumb, left-index-finger, left-middle-finger,"
            echo "  left-ring-finger, left-little-finger"
            read -p "Ingresa el nombre del dedo: " FINGER
            ;;
        *) FINGER="right-index-finger" ;;
    esac

    echo ""
    echo -e "${YELLOW}→${NC} Iniciando registro de huella para: ${GREEN}$FINGER${NC}"
    echo ""

    # Registrar la huella
    if sudo -u "$REAL_USER" fprintd-enroll -f "$FINGER"; then
        echo ""
        echo -e "${GREEN}✓${NC} ¡Huella registrada exitosamente!"
    else
        echo ""
        echo -e "${RED}✗${NC} Error al registrar la huella"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}[5/5]${NC} Saltando registro de huellas (ya existen)"
    echo ""
fi

# Probar autenticación (solo si no se saltó y se acaba de registrar)
if [ "$SKIP_VERIFY" = false ] && [ "$SKIP_ENROLL_SECTION" = false ]; then
    echo -e "${YELLOW}→${NC} Probando huella (quita el dedo, esperando 3s)..."
    sleep 3

    if sudo -u "$REAL_USER" fprintd-verify 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Huella verificada correctamente"
    else
        echo -e "${YELLOW}⚠${NC} No se pudo verificar (prueba con: fprintd-verify)"
    fi
    echo ""
fi

# Resumen final
echo ""
echo -e "${GREEN}✓${NC} Configuración completada"
if [ "$SKIP_ENROLL_SECTION" = false ] && [ -n "$FINGER" ]; then
    echo -e "${GREEN}✓${NC} Nueva huella registrada: $FINGER"
elif [ "$HAS_FINGERPRINTS" = true ]; then
    echo -e "${GREEN}✓${NC} ${FINGERPRINT_COUNT} huella(s) activa(s)"
else
    echo -e "${BLUE}ℹ${NC} Autenticación por huella disponible - registra con: ${BLUE}fprintd-enroll${NC}"
fi
echo ""
