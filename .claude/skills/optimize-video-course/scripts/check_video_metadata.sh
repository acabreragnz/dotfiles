#!/bin/bash
#
# check_video_metadata.sh - Check optimization metadata of a video
# Usage: ./check_video_metadata.sh <video.mp4>
#

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <video.mp4>"
    exit 1
fi

VIDEO_FILE="$1"

if [ ! -f "$VIDEO_FILE" ]; then
    echo "Error: File not found: $VIDEO_FILE"
    exit 1
fi

if ! command -v ffprobe &> /dev/null; then
    echo "Error: ffprobe is not installed"
    exit 1
fi

echo "=========================================="
echo "Metadata for: $(basename "$VIDEO_FILE")"
echo "=========================================="

# Get comment field
COMMENT=$(ffprobe -v quiet -show_entries format_tags=comment -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE" 2>/dev/null || echo "N/A")

# Parse metadata from comment (supports both JSON and legacy format)
if [[ "$COMMENT" =~ ^\{.*\"optimized\":true.*\}$ ]]; then
    # New JSON format
    OPTIMIZED="yes"

    # Parse JSON fields (using grep/sed for compatibility, jq is better if available)
    if command -v jq &> /dev/null; then
        OPT_DATE=$(echo "$COMMENT" | jq -r '.date // "N/A"')
        OPT_TOOL=$(echo "$COMMENT" | jq -r '.tool // "N/A"')
        ORIG_SIZE=$(echo "$COMMENT" | jq -r '.original_mb // "N/A"')
        CRF=$(echo "$COMMENT" | jq -r '.crf // "N/A"')
        PRESET=$(echo "$COMMENT" | jq -r '.preset // "N/A"')
        AUDIO_BITRATE=$(echo "$COMMENT" | jq -r '.audio_bitrate // "N/A"')
    else
        # Fallback parsing without jq (less robust)
        OPT_DATE=$(echo "$COMMENT" | grep -oP '"date":"\K[^"]+' || echo "N/A")
        OPT_TOOL=$(echo "$COMMENT" | grep -oP '"tool":"\K[^"]+' || echo "N/A")
        ORIG_SIZE=$(echo "$COMMENT" | grep -oP '"original_mb":\K[0-9.]+' || echo "N/A")
        CRF=$(echo "$COMMENT" | grep -oP '"crf":\K[0-9]+' || echo "N/A")
        PRESET=$(echo "$COMMENT" | grep -oP '"preset":"\K[^"]+' || echo "N/A")
        AUDIO_BITRATE=$(echo "$COMMENT" | grep -oP '"audio_bitrate":"\K[^"]+' || echo "N/A")
    fi
elif [[ "$COMMENT" == "[OPTIMIZED]"* ]]; then
    # Legacy format (backward compatibility)
    OPTIMIZED="yes"
    OPT_DATE=$(echo "$COMMENT" | grep -oP 'date=\K[^|]+' || echo "N/A")
    OPT_TOOL=$(echo "$COMMENT" | grep -oP 'tool=\K[^|]+' || echo "N/A")
    ORIG_SIZE=$(echo "$COMMENT" | grep -oP 'original_mb=\K[^|]+' || echo "N/A")
    CRF=$(echo "$COMMENT" | grep -oP 'crf=\K[^|]*' || echo "N/A")
    PRESET="N/A (legacy format)"
    AUDIO_BITRATE="N/A (legacy format)"
else
    OPTIMIZED="no"
    OPT_DATE="N/A"
    OPT_TOOL="N/A"
    ORIG_SIZE="N/A"
    CRF="N/A"
    PRESET="N/A"
    AUDIO_BITRATE="N/A"
fi

# Current size
CURRENT_SIZE=$(stat -c%s "$VIDEO_FILE" | awk '{printf "%.2f", $1/1024/1024}')

echo ""
echo "Optimization status:    $OPTIMIZED"
echo "Optimization date:      $OPT_DATE"
echo "Tool:                   $OPT_TOOL"
echo "Original size:          $ORIG_SIZE MB"
echo "Current size:           $CURRENT_SIZE MB"
echo "CRF used:               $CRF"
echo "Preset:                 $PRESET"
echo "Audio bitrate:          $AUDIO_BITRATE"
echo "Full comment:           $COMMENT"
echo ""

if [ "$OPTIMIZED" = "yes" ]; then
    echo "✓ This video HAS BEEN OPTIMIZED"
    if [ "$ORIG_SIZE" != "N/A" ] && [ "$ORIG_SIZE" != "" ]; then
        REDUCTION=$(echo "$ORIG_SIZE $CURRENT_SIZE" | awk '{printf "%.2f", $1 - $2}')
        REDUCTION_PCT=$(echo "$ORIG_SIZE $CURRENT_SIZE" | awk '{printf "%.0f", (($1 - $2) / $1) * 100}')
        echo "  Reduction: ${REDUCTION}MB (${REDUCTION_PCT}%)"
    fi
else
    echo "✗ This video has NOT been optimized"
fi

echo "=========================================="
