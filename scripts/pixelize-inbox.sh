#!/usr/bin/env bash
# Procesa imágenes dropeadas en .pixelize/full/ o .pixelize/quick/
# Corre pixelize.py con el perfil correspondiente y mueve el original al directorio generado.

PIXELIZE="$HOME/Pictures/.inbox/.pixelize"
SCRIPT="$HOME/scripts/pixelize.py"

process_dir() {
    local profile="$1"
    local inbox="$PIXELIZE/$profile"

    for img in "$inbox"/*.{jpg,jpeg,png,webp}; do
        [ -f "$img" ] || continue

        name=$(basename "$img")
        stem="${name%.*}"
        ext="${name##*.}"

        # Renombrar si el nombre parece genérico
        if echo "$stem" | grep -qiE "^(pasted[[:space:]_-]*image|screenshot|captura|image|img|photo|foto)[[:space:]_-]*[0-9]*$"; then
            newname="$(date '+%Y-%m-%d_%H-%M-%S').$ext"
            mv "$img" "$inbox/$newname"
            img="$inbox/$newname"
            name="$newname"
            stem="${name%.*}"
            echo "[pixelize] Renombrado → $newname"
        fi

        echo "[pixelize/$profile] Procesando: $name"

        if "$SCRIPT" "$img" --profile "$profile" --output-dir "$inbox/$stem"; then
            if [ -d "$inbox/$stem" ]; then
                mv "$img" "$inbox/$stem/$name" \
                    && echo "[pixelize/$profile] OK: $name → $stem/"
            else
                echo "[pixelize/$profile] Sin caras detectadas: $name (sin mover)"
            fi
        else
            echo "[pixelize/$profile] ERROR procesando: $name"
        fi
    done

    # Directorios dropeados → pixelize.py los procesa enteros, se mueven a done/
    # (los _anonymized/ quedan adentro del dir, no hay un generated dir único donde mover el original)
    local done_dir="$inbox/done"
    mkdir -p "$done_dir"
    for dir in "$inbox"/*/; do
        [ -d "$dir" ] || continue
        [[ "$dir" == "$done_dir"/ ]] && continue

        name=$(basename "$dir")
        echo "[pixelize/$profile] Procesando directorio: $name"

        "$SCRIPT" "$dir" --profile "$profile" \
            && mv "$dir" "$done_dir/$name" \
            && echo "[pixelize/$profile] OK: $name → done/" \
            || echo "[pixelize/$profile] ERROR procesando directorio: $name"
    done
}

process_dir full
process_dir quick
