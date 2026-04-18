#!/usr/bin/env bash
# Procesa imágenes dropeadas en .pixelize/full/ o .pixelize/quick/
# Corre pixelize.py con el perfil correspondiente y mueve el original al directorio generado.

PIXELIZE="$HOME/Pictures/.inbox/.pixelize"
SCRIPT="$HOME/scripts/pixelize.py"

process_dir() {
    local profile="$1"
    local inbox="$PIXELIZE/$profile"
    local done_dir="$inbox/done"

    # Snapshot de directorios dropeados ANTES de procesar imágenes.
    # Se excluyen dirs que ya tienen .pixelize_done (outputs de corridas anteriores).
    local -a dropped_dirs=()
    for d in "$inbox"/*/; do
        [ -d "$d" ] || continue
        [[ "$d" == "$done_dir"/ ]] && continue
        [ -f "${d}.pixelize_done" ] && continue
        dropped_dirs+=("$d")
    done

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
                    && touch "$inbox/$stem/.pixelize_done" \
                    && echo "[pixelize/$profile] OK: $name → $stem/"
            else
                echo "[pixelize/$profile] Sin caras detectadas: $name (sin mover)"
            fi
        else
            echo "[pixelize/$profile] ERROR procesando: $name"
        fi
    done

    # Directorios dropeados por el usuario → procesar entero y mover a done/
    if [ ${#dropped_dirs[@]} -gt 0 ]; then
        mkdir -p "$done_dir"
        for dir in "${dropped_dirs[@]}"; do
            [ -d "$dir" ] || continue
            name=$(basename "$dir")
            echo "[pixelize/$profile] Procesando directorio: $name"

            "$SCRIPT" "$dir" --profile "$profile" \
                && mv "$dir" "$done_dir/$name" \
                && echo "[pixelize/$profile] OK: $name → done/" \
                || echo "[pixelize/$profile] ERROR procesando directorio: $name"
        done
    fi
}

process_dir full
process_dir quick
