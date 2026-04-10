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
    stem="${name%.*}"
    ext="${name##*.}"

    # Renombrar si el nombre parece genérico (Pasted image, screenshot, captura, etc.)
    if echo "$stem" | grep -qiE "^(pasted[[:space:]_-]*image|screenshot|captura|image|img|photo|foto)[[:space:]_-]*[0-9]*$"; then
        newname="$(date '+%Y-%m-%d_%H-%M-%S').$ext"
        mv "$img" "$INBOX/$newname"
        img="$INBOX/$newname"
        name="$newname"
        stem="${name%.*}"
        echo "[anonymize-inbox] Renombrado: $(basename "$img") → $newname"
    fi

    echo "[anonymize-inbox] Procesando: $name"

    "$SCRIPT" "$img" --output-dir "$INBOX/${stem}_anonymized" \
        && mv "$img" "$DONE/$name" \
        && echo "[anonymize-inbox] OK: $name → done/" \
        || echo "[anonymize-inbox] ERROR procesando: $name"
done
