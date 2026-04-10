#!/usr/bin/env bash
# Procesa todas las imágenes en ~/Pictures/.inbox/
# Corre el script anonymize_faces.py en cada una y la mueve a .inbox/done/

INBOX="$HOME/Pictures/.inbox"
DONE="$INBOX/done"
SCRIPT="$HOME/scripts/anonymize_faces.py"

mkdir -p "$DONE"

for img in "$INBOX"/*.{jpg,jpeg,png,webp}; do
    [ -f "$img" ] || continue

    name=$(basename "$img")
    echo "[anonymize-inbox] Procesando: $name"

    "$SCRIPT" "$img" --output-dir "$INBOX/${name%.*}_anonymized" \
        && mv "$img" "$DONE/$name" \
        && echo "[anonymize-inbox] OK: $name → done/" \
        || echo "[anonymize-inbox] ERROR procesando: $name"
done
