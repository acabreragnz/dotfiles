#!/usr/bin/env bash
# Procesa videos dropeados en .capturas/full/, .capturas/medium/ o .capturas/low/
# Corre video_capture.py con el modo correspondiente (siempre con --pixelize)
# y mueve el original a done/

CAPTURAS="$HOME/Pictures/.inbox/.capturas"
SCRIPT="$HOME/scripts/video_capture.py"

process_dir() {
    local mode="$1"
    local pixelize="$2"   # "yes" | "no"
    local inbox="$CAPTURAS/$mode"
    local done_dir="$inbox/done"

    mkdir -p "$done_dir"

    for vid in "$inbox"/*.{mp4,mkv,avi,mov,webm,m4v,flv,wmv}; do
        [ -f "$vid" ] || continue

        name=$(basename "$vid")
        stem="${name%.*}"

        # VLC recordings de la cámara IP no tienen metadata de rotación → forzar 180°
        rotate_flag=""
        if echo "$name" | grep -qi "^vlc-record"; then
            rotate_flag="--rotate 180"
        fi

        pixelize_flag=""
        [ "$pixelize" = "yes" ] && pixelize_flag="--pixelize"

        echo "[capturas/$mode] Procesando: $name (pixelize=$pixelize)"

        local out_dir="$done_dir/${stem}_capturas_${mode}"

        "$SCRIPT" "$vid" "$mode" $pixelize_flag $rotate_flag --output "$out_dir" \
            && mv "$vid" "$out_dir/$name" \
            && echo "[capturas/$mode] OK: $name → $out_dir/" \
            || echo "[capturas/$mode] ERROR procesando: $name"
    done
}

process_dir full    yes
process_dir medium  yes
process_dir low     yes
process_dir gphotos no
