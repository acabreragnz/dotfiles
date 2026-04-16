#!/usr/bin/env bash
# Procesa videos dropeados en .capturas/full/, .capturas/medium/ o .capturas/low/
# Corre video_capture.py con el modo correspondiente (siempre con --pixelize)
# y mueve el original a done/

CAPTURAS="$HOME/Pictures/.inbox/.capturas"
SCRIPT="$HOME/scripts/video_capture.py"

process_dir() {
    local mode="$1"
    local inbox="$CAPTURAS/$mode"
    local done_dir="$inbox/done"

    mkdir -p "$done_dir"

    for vid in "$inbox"/*.{mp4,mkv,avi,mov,webm,m4v,flv,wmv}; do
        [ -f "$vid" ] || continue

        name=$(basename "$vid")
        stem="${name%.*}"

        echo "[capturas/$mode] Procesando: $name"

        "$SCRIPT" "$vid" "$mode" --pixelize --output "$done_dir/${stem}_capturas_${mode}" \
            && mv "$vid" "$done_dir/$name" \
            && echo "[capturas/$mode] OK: $name → done/" \
            || echo "[capturas/$mode] ERROR procesando: $name"
    done
}

process_dir full
process_dir medium
process_dir low
