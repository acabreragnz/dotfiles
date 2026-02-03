#!/bin/bash
#
# add_metadata_to_video.sh - Agrega metadata de optimización a un video sin re-comprimir
# Uso: ./add_metadata_to_video.sh --input <video.mp4> --original-size <MB> [--date YYYY-MM-DD] [--crf N]
#

set -euo pipefail

INPUT_FILE=""
ORIGINAL_SIZE=""
OPT_DATE=$(date +%Y-%m-%d)
CRF="23"

show_usage() {
    cat <<EOF
Uso: $0 --input <video.mp4> --original-size <MB> [opciones]

Argumentos requeridos:
  --input FILE          Ruta al video ya optimizado
  --original-size MB    Tamaño original en MB antes de optimizar

Argumentos opcionales:
  --date YYYY-MM-DD     Fecha de optimización (default: hoy)
  --crf N               CRF usado en la optimización (default: 23)

Este script agrega metadata sin re-comprimir el video (operación rápida).

Ejemplo:
  $0 --input "video-optimizado.mp4" --original-size 106.52 --crf 23

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_FILE="$2"
            shift 2
            ;;
        --original-size)
            ORIGINAL_SIZE="$2"
            shift 2
            ;;
        --date)
            OPT_DATE="$2"
            shift 2
            ;;
        --crf)
            CRF="$2"
            shift 2
            ;;
        --help)
            show_usage
            ;;
        *)
            echo "Error: Argumento desconocido: $1"
            show_usage
            ;;
    esac
done

if [ -z "$INPUT_FILE" ] || [ -z "$ORIGINAL_SIZE" ]; then
    echo "Error: --input y --original-size son requeridos"
    show_usage
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Archivo no encontrado: $INPUT_FILE"
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg no está instalado"
    exit 1
fi

echo "[INFO] Agregando metadata a: $(basename "$INPUT_FILE")"
echo "[INFO] Tamaño original: ${ORIGINAL_SIZE}MB"

# Crear archivo temporal
TEMP_FILE="${INPUT_FILE%.mp4}_temp.mp4"

# Copiar video sin re-comprimir, solo agregando metadata
ffmpeg -i "$INPUT_FILE" \
    -c copy \
    -metadata optimized="yes" \
    -metadata optimization_date="$OPT_DATE" \
    -metadata optimization_tool="claude-optimize-video-course" \
    -metadata original_size_mb="$ORIGINAL_SIZE" \
    -metadata crf="$CRF" \
    -metadata comment="Optimized for educational content - preserves text clarity" \
    -y "$TEMP_FILE" \
    -loglevel error

if [ $? -eq 0 ]; then
    # Reemplazar archivo original con el que tiene metadata
    mv "$TEMP_FILE" "$INPUT_FILE"
    echo "[SUCCESS] Metadata agregada exitosamente"
    echo ""

    # Mostrar metadata
    ~/.claude/skills/optimize-video-course/scripts/check_video_metadata.sh "$INPUT_FILE"
else
    echo "[ERROR] Falló al agregar metadata"
    rm -f "$TEMP_FILE"
    exit 1
fi
