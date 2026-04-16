#!/usr/bin/env bash
# Procesa videos dropeados en .capturas/full/, .capturas/medium/ o .capturas/low/
# Corre video_capture.py con el modo correspondiente (siempre con --pixelize)
# y mueve el original a done/

CAPTURAS="$HOME/Pictures/.inbox/.capturas"
SCRIPT="$HOME/scripts/video_capture.py"

process_dir() {
    local mode="$1"
    local pixelize="$2"   # "yes" | "no"
    local capture_mode="${3:-$mode}"   # modo para video_capture.py (default: igual al dir)
    local inbox="$CAPTURAS/$mode"
    local done_dir="$inbox/done"

    mkdir -p "$done_dir"

    for vid in "$inbox"/*.{mp4,mkv,avi,mov,webm,m4v,flv,wmv}; do
        [ -f "$vid" ] || continue

        name=$(basename "$vid")
        stem="${name%.*}"

        # VLC recordings y grabaciones rec_* de la cámara IP → forzar 180°
        rotate_flag=""
        if echo "$name" | grep -qiE "^vlc-record|^rec_"; then
            rotate_flag="--rotate 180"
        fi

        pixelize_flag=""
        [ "$pixelize" = "yes" ] && pixelize_flag="--pixelize"

        echo "[capturas/$mode] Procesando: $name (pixelize=$pixelize)"

        local out_dir="$done_dir/${stem}_capturas_${mode}"

        "$SCRIPT" "$vid" "$capture_mode" $pixelize_flag $rotate_flag --output "$out_dir" &
        local pid=$!

        # Watchdog: si el archivo fuente desaparece, matar el proceso
        while kill -0 "$pid" 2>/dev/null; do
            if [ ! -f "$vid" ]; then
                echo "[capturas/$mode] Archivo fuente desapareció, abortando: $name"
                kill "$pid" 2>/dev/null
                break
            fi
            sleep 10
        done
        wait "$pid"
        local exit_code=$?

        if [ -f "$vid" ] && [ $exit_code -eq 0 ]; then
            mv "$vid" "$out_dir/$name" \
                && echo "[capturas/$mode] OK: $name → $out_dir/"
        elif [ $exit_code -ne 0 ]; then
            echo "[capturas/$mode] ERROR procesando: $name (exit $exit_code)"
        fi
    done
}

process_dir full    yes
process_dir medium  yes
process_dir low     yes
process_dir gphotos no full
