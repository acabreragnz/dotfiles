#!/bin/bash
#
# optimize_video.sh - Optimize course videos with intelligent compression
# Usage: ./optimize_video.sh --input <file> --year <year> --course <name> --lesson <num> [options]
#

set -euo pipefail

# ============================================================================
# CONFIGURABLE VARIABLES
# ============================================================================
CRF=23
PRESET="medium"
AUDIO_BITRATE="128k"
MAX_HEIGHT=""
DRY_RUN=false
DELETE_ORIGINALS=false

# Required variables (set via arguments)
INPUT_FILE=""
YEAR=""
COURSE=""
MODULE=""
SECTION=""
LESSON=""
TITLE=""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
show_usage() {
    cat <<EOF
Usage: $0 --input <file> --year <year> --course <name> --lesson <num> [options]

Required arguments:
  --input FILE      Path to input video file
  --year YYYY       Course year (e.g., 2026)
  --course NAME     Course name (e.g., "OWASP Top 10 · Web Security")
  --lesson NUM      Lesson number (e.g., 1, 2, 3)

Optional arguments:
  --module NUM          Module number (for 2+ level hierarchy)
  --section NUM         Section number (for 3 level hierarchy)
  --title TEXT          Descriptive title (generated from filename if omitted)
  --crf N               Custom CRF value (default: $CRF, range: 18-28)
  --preset PRESET       Encoding preset (default: $PRESET, options: fast/medium/slow/veryslow)
  --audio-bitrate RATE  Audio bitrate (default: $AUDIO_BITRATE, e.g., 96k/128k/192k)
  --max-height N        Max video height in pixels (e.g., 1080, 720, 480). Scales down if taller. Omit to keep original.
  --delete-originals    Delete original files after successful optimization (default: keep)
  --dry-run             Show what would be done without executing
  --help                Show this help

Output format:
  YYYY - Course - [Hierarchy] - Title.mp4

Hierarchy examples:
  Flat:            YYYY - Course - L01 - Title.mp4
  With modules:    YYYY - Course - M01 - L02 - Title.mp4
  With sections:   YYYY - Course - M01 - S02 - L03 - Title.mp4

Examples:
  # Flat structure
  $0 --input "01 - Intro.mp4" --year 2026 --course "React Basics" --lesson 1

  # With modules
  $0 --input "video.mp4" --year 2026 --course "OWASP Top 10" --module 1 --lesson 2 --title "Why Learn OWASP"

  # With modules and sections
  $0 --input "video.mp4" --year 2024 --course "Clean Code" --module 1 --section 2 --lesson 5 --title "DIP"

  # Custom quality settings
  $0 --input "video.mp4" --year 2026 --course "Course" --lesson 1 --crf 18 --preset slow --audio-bitrate 192k

EOF
    exit 0
}

log_info() {
    echo "[INFO] $*"
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_success() {
    echo "[SUCCESS] $*"
}

format_size() {
    local size=$1
    if command -v numfmt &> /dev/null; then
        numfmt --to=iec-i --suffix=B --format="%.2f" "$size"
    else
        echo "$size bytes"
    fi
}

sanitize_title() {
    local title="$1"
    # Remove number prefixes (e.g., "2 - Title" -> "Title")
    title=$(echo "$title" | sed -E 's/^[0-9]+[[:space:]]*-[[:space:]]*//')
    # Remove .mp4 extension
    title="${title%.mp4}"
    # Replace underscores with spaces
    title=$(echo "$title" | tr '_' ' ')
    # Clean multiple spaces
    title=$(echo "$title" | sed 's/  */ /g')
    # Trim leading/trailing spaces
    title=$(echo "$title" | sed 's/^ *//; s/ *$//')
    echo "$title"
}

check_dependencies() {
    local missing=()

    if ! command -v ffmpeg &> /dev/null; then
        missing+=("ffmpeg")
    fi

    if ! command -v ffprobe &> /dev/null; then
        missing+=("ffprobe")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        log_error "Install with: sudo apt install ffmpeg"
        exit 1
    fi
}

# ============================================================================
# PARSEO DE ARGUMENTOS
# ============================================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --input)
                INPUT_FILE="$2"
                shift 2
                ;;
            --year)
                YEAR="$2"
                shift 2
                ;;
            --course)
                COURSE="$2"
                shift 2
                ;;
            --module)
                MODULE="$2"
                shift 2
                ;;
            --section)
                SECTION="$2"
                shift 2
                ;;
            --lesson)
                LESSON="$2"
                shift 2
                ;;
            --title)
                TITLE="$2"
                shift 2
                ;;
            --crf)
                CRF="$2"
                shift 2
                ;;
            --preset)
                PRESET="$2"
                shift 2
                ;;
            --audio-bitrate)
                AUDIO_BITRATE="$2"
                shift 2
                ;;
            --max-height)
                MAX_HEIGHT="$2"
                shift 2
                ;;
            --delete-originals)
                DELETE_ORIGINALS=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                show_usage
                ;;
            *)
                log_error "Unknown argument: $1"
                show_usage
                ;;
        esac
    done

    # Validate required arguments
    if [ -z "$INPUT_FILE" ]; then
        log_error "Argument --input is required"
        show_usage
    fi

    if [ -z "$YEAR" ]; then
        log_error "Argument --year is required"
        show_usage
    fi

    if [ -z "$COURSE" ]; then
        log_error "Argument --course is required"
        show_usage
    fi

    if [ -z "$LESSON" ]; then
        log_error "Argument --lesson is required"
        show_usage
    fi

    # If no title provided, extract from filename
    if [ -z "$TITLE" ]; then
        local basename
        basename=$(basename "$INPUT_FILE")
        TITLE=$(sanitize_title "$basename")
        log_info "Title auto-generated from filename: $TITLE"
    fi
}

# ============================================================================
# VALIDATION
# ============================================================================
validate_input() {
    if [ ! -f "$INPUT_FILE" ]; then
        log_error "File not found: $INPUT_FILE"
        exit 1
    fi

    if ! [[ "$YEAR" =~ ^[0-9]{4}$ ]]; then
        log_error "Invalid year: $YEAR (must be YYYY format)"
        exit 1
    fi

    if [ -n "$MODULE" ] && ! [[ "$MODULE" =~ ^[0-9]+$ ]]; then
        log_error "Invalid module number: $MODULE"
        exit 1
    fi

    if [ -n "$SECTION" ] && ! [[ "$SECTION" =~ ^[0-9]+$ ]]; then
        log_error "Invalid section number: $SECTION"
        exit 1
    fi

    if ! [[ "$LESSON" =~ ^[0-9]+$ ]]; then
        log_error "Invalid lesson number: $LESSON"
        exit 1
    fi

    if ! [[ "$CRF" =~ ^[0-9]+$ ]] || [ "$CRF" -lt 18 ] || [ "$CRF" -gt 28 ]; then
        log_error "Invalid CRF: $CRF (must be between 18-28)"
        exit 1
    fi

    # Validate preset
    case "$PRESET" in
        ultrafast|superfast|veryfast|faster|fast|medium|slow|slower|veryslow)
            ;;
        *)
            log_error "Invalid preset: $PRESET (must be one of: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)"
            exit 1
            ;;
    esac

    # Validate audio bitrate format (e.g., 96k, 128k, 192k)
    if ! [[ "$AUDIO_BITRATE" =~ ^[0-9]+k$ ]]; then
        log_error "Invalid audio bitrate: $AUDIO_BITRATE (must be format like 128k)"
        exit 1
    fi

    # Validate max-height if provided
    if [ -n "$MAX_HEIGHT" ]; then
        if ! [[ "$MAX_HEIGHT" =~ ^[0-9]+$ ]] || [ "$MAX_HEIGHT" -lt 240 ] || [ "$MAX_HEIGHT" -gt 2160 ]; then
            log_error "Invalid max-height: $MAX_HEIGHT (must be between 240-2160 pixels)"
            exit 1
        fi
    fi
}

# ============================================================================
# GENERACIÓN DE NOMBRE DE SALIDA
# ============================================================================
generate_output_name() {
    local input_dir
    local hierarchy=""
    local output_filename

    input_dir=$(dirname "$INPUT_FILE")

    # Construir jerarquía según qué parámetros estén presentes
    if [ -n "$MODULE" ]; then
        hierarchy="M$(printf "%02d" "$MODULE")"
    fi

    if [ -n "$SECTION" ]; then
        hierarchy="${hierarchy} - S$(printf "%02d" "$SECTION")"
    fi

    hierarchy="${hierarchy} - L$(printf "%02d" "$LESSON")"

    # Limpiar posible guion al inicio (si no hay module)
    hierarchy=$(echo "$hierarchy" | sed 's/^ - //')

    # Formato: YYYY - Course - Hierarchy - Title.mp4
    output_filename="${YEAR} - ${COURSE} - ${hierarchy} - ${TITLE}.mp4"
    OUTPUT_FILE="${input_dir}/${output_filename}"

    log_info "Nombre de salida: $output_filename"
}

# ============================================================================
# VERIFICACIÓN DE VIDEO YA OPTIMIZADO
# ============================================================================
check_already_optimized() {
    # Verificar si el archivo de entrada ya tiene metadata de optimización en el campo comment
    if command -v ffprobe &> /dev/null; then
        local comment
        comment=$(ffprobe -v quiet -show_entries format_tags=comment -of default=noprint_wrappers=1:nokey=1 "$INPUT_FILE" 2>/dev/null)

        if [[ "$comment" == "[OPTIMIZED]"* ]]; then
            # Parsear metadata del comment
            local opt_date=$(echo "$comment" | grep -oP 'date=\K[^|]+')
            local original_size=$(echo "$comment" | grep -oP 'original_mb=\K[^|]+')

            log_info "Video already optimized on $opt_date (original: ${original_size}MB)"
            log_info "Skipping: $(basename "$INPUT_FILE")"
            exit 0
        fi
    fi

    # Verificación adicional: buscar archivo con el patrón de nombre optimizado
    local input_dir
    local search_pattern

    input_dir=$(dirname "$INPUT_FILE")

    # Construir patrón de búsqueda basado en jerarquía y título
    local hierarchy_pattern=""
    if [ -n "$MODULE" ]; then
        hierarchy_pattern="M$(printf "%02d" "$MODULE")"
    fi
    if [ -n "$SECTION" ]; then
        hierarchy_pattern="${hierarchy_pattern} - S$(printf "%02d" "$SECTION")"
    fi
    hierarchy_pattern="${hierarchy_pattern} - L$(printf "%02d" "$LESSON")"
    hierarchy_pattern=$(echo "$hierarchy_pattern" | sed 's/^ - //')

    search_pattern="${YEAR} - ${COURSE} - ${hierarchy_pattern} - ${TITLE}.mp4"

    if [ -f "${input_dir}/${search_pattern}" ]; then
        log_info "Video already optimized (by filename), skipping: $search_pattern"
        exit 0
    fi
}

# ============================================================================
# COMPRESSION
# ============================================================================
compress_video() {
    local start_time
    local end_time
    local duration
    local input_size_mb
    local optimization_date

    log_info "Compressing: $INPUT_FILE"
    log_info "Settings: CRF=$CRF, PRESET=$PRESET, AUDIO=$AUDIO_BITRATE"
    if [ -n "$MAX_HEIGHT" ]; then
        log_info "Max height: $MAX_HEIGHT (will scale down if needed)"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would execute: ffmpeg -i \"$INPUT_FILE\" -c:v libx264 -crf $CRF -preset $PRESET ..."
        return 0
    fi

    # Calculate original size for metadata (use LC_NUMERIC=C to ensure dot decimal separator)
    input_size_mb=$(LC_NUMERIC=C stat -c%s "$INPUT_FILE" | awk '{printf "%.2f", $1/1024/1024}')
    optimization_date=$(date +%Y-%m-%d)

    # Build video filter string if max-height is set
    local vf_filter=""
    if [ -n "$MAX_HEIGHT" ]; then
        # Scale only if height > MAX_HEIGHT, preserving aspect ratio
        # -2 ensures width is divisible by 2 (required for H.264)
        vf_filter="-vf scale=-2:min(ih\\,$MAX_HEIGHT)"
    fi

    # Create JSON metadata in comment field
    local metadata_json="{\"optimized\":true,\"date\":\"$optimization_date\",\"tool\":\"claude-optimize-video-course\",\"original_mb\":$input_size_mb,\"crf\":$CRF,\"preset\":\"$PRESET\",\"audio_bitrate\":\"$AUDIO_BITRATE\""
    if [ -n "$MAX_HEIGHT" ]; then
        metadata_json="$metadata_json,\"max_height\":$MAX_HEIGHT"
    fi
    metadata_json="$metadata_json}"

    start_time=$(date +%s)

    ffmpeg -i "$INPUT_FILE" \
        -c:v libx264 \
        -crf "$CRF" \
        -preset "$PRESET" \
        -tune stillimage \
        -aq-mode 3 \
        $vf_filter \
        -c:a aac \
        -b:a "$AUDIO_BITRATE" \
        -movflags +faststart \
        -metadata comment="$metadata_json" \
        -y "$OUTPUT_FILE" \
        -loglevel warning -stats

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    log_success "Compression completed in ${duration}s"
    log_info "Metadata embedded (JSON): optimized=true, crf=$CRF, original_size=${input_size_mb}MB"
}

# ============================================================================
# POST-PROCESSING VERIFICATION
# ============================================================================
verify_output() {
    if [ "$DRY_RUN" = true ]; then
        return 0
    fi

    log_info "Verifying output file..."

    if [ ! -f "$OUTPUT_FILE" ]; then
        log_error "Output file was not created: $OUTPUT_FILE"
        exit 1
    fi

    # Verify with ffprobe that video is playable
    if ! ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE" &> /dev/null; then
        log_error "Output video is corrupted or not playable"
        rm -f "$OUTPUT_FILE"
        exit 1
    fi

    log_success "Video verified successfully"

    # Delete original if requested and verification passed
    if [ "$DELETE_ORIGINALS" = true ]; then
        log_info "Deleting original file: $INPUT_FILE"
        rm -f "$INPUT_FILE"
        log_success "Original file deleted"
    fi
}

# ============================================================================
# STATISTICS
# ============================================================================
show_statistics() {
    local input_size
    local output_size
    local reduction
    local reduction_pct

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Statistics not available in dry-run mode"
        return 0
    fi

    # Check if input file still exists (may have been deleted)
    if [ -f "$INPUT_FILE" ]; then
        input_size=$(stat -c%s "$INPUT_FILE")
    else
        # File was deleted, calculate from metadata
        local input_size_mb=$(ffprobe -v quiet -show_entries format_tags=comment -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE" | grep -oP 'original_mb":\K[0-9.]+')
        if [ -n "$input_size_mb" ]; then
            input_size=$(echo "$input_size_mb * 1024 * 1024" | bc | cut -d. -f1)
        else
            log_info "Cannot calculate size reduction (original file deleted and no metadata)"
            return 0
        fi
    fi

    output_size=$(stat -c%s "$OUTPUT_FILE")
    reduction=$((input_size - output_size))
    reduction_pct=$((100 * reduction / input_size))

    echo ""
    echo "=========================================="
    echo "Original:  $(format_size $input_size)"
    echo "Optimized: $(format_size $output_size)"
    echo "Reduction: $(format_size $reduction) (${reduction_pct}%)"
    echo "=========================================="
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    parse_args "$@"
    check_dependencies
    validate_input
    check_already_optimized
    generate_output_name
    compress_video
    verify_output
    show_statistics

    log_success "Process completed successfully"
}

main "$@"
