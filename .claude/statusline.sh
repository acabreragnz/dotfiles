#!/bin/bash
# Force C locale for numeric formatting
export LC_NUMERIC=C

# ANSI color codes (bash $'...' syntax — interpreted at parse time, not by echo)
RESET=$'\033[0m'
RED=$'\033[31m'
YELLOW=$'\033[33m'
GREEN=$'\033[32m'
BLUE=$'\033[34m'
CYAN=$'\033[36m'
MAGENTA=$'\033[35m'
BRIGHT_YELLOW=$'\033[93m'
DIM=$'\033[90m'

# Read JSON input from stdin
input=$(cat)
echo "$input" > /tmp/statusline-debug.json

# Extract values
MODEL_NAME=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
OUTPUT_STYLE=$(echo "$input" | jq -r '.output_style.name // empty')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir')
DIR_NAME=$(basename "$CURRENT_DIR")
WINDOW_SIZE=$(echo "$input" | jq -r '.context_window.context_window_size // 200000')

# Calculate used input tokens (input + cache creation + cache read)
INPUT_TOKENS=$(echo "$input" | jq -r '
  (.context_window.current_usage // {}) |
  ((.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0))
')

# Percentage of context window used (against full window size)
REAL_PCT=$(echo "scale=1; $INPUT_TOKENS / $WINDOW_SIZE * 100" | bc -l 2>/dev/null || echo "0")
REAL_PCT_FMT=$(printf "%.1f" "$REAL_PCT")

# Token counts in k
USED_K=$(echo "scale=0; $INPUT_TOKENS / 1000" | bc)
TOTAL_K=$(echo "scale=0; $WINDOW_SIZE / 1000" | bc)

# Color based on real percentage (against effective limit)
if (( $(echo "$REAL_PCT > 80" | bc -l) )); then
    CTX_COLOR="$RED"
elif (( $(echo "$REAL_PCT > 60" | bc -l) )); then
    CTX_COLOR="$YELLOW"
else
    CTX_COLOR="$GREEN"
fi

# Worktree indicator (takes priority over regular git branch)
WORKTREE_NAME=$(echo "$input" | jq -r '.worktree.name // empty')
GIT_BRANCH=""
if [ -n "$WORKTREE_NAME" ]; then
    WORKTREE_BRANCH=$(echo "$input" | jq -r '.worktree.branch // empty')
    ORIG_BRANCH=$(echo "$input" | jq -r '.worktree.original_branch // empty')
    BRANCH_LABEL="${WORKTREE_BRANCH:-$WORKTREE_NAME}"
    GIT_BRANCH=" ${MAGENTA}|${RESET} ${BRIGHT_YELLOW}⎇ ${BRANCH_LABEL}${RESET}"
    [ -n "$ORIG_BRANCH" ] && GIT_BRANCH="${GIT_BRANCH} ${DIM}(from ${ORIG_BRANCH})${RESET}"
elif git -C "$CURRENT_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git -C "$CURRENT_DIR" branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        GIT_BRANCH=" ${MAGENTA}|${RESET} ${CYAN}${BRANCH}${RESET}"
    fi
fi

# Rate limits — helpers to format countdown from a unix epoch resets_at value
format_countdown_hours() {
    local resets_at="$1"
    local now
    now=$(date +%s)
    local diff=$(( resets_at - now ))
    if (( diff <= 0 )); then
        echo "r now"
        return
    fi
    local hours=$(( diff / 3600 ))
    local mins=$(( (diff % 3600) / 60 ))
    if (( hours > 0 )); then
        printf "r in %dh%02dm" "$hours" "$mins"
    else
        printf "r in %dm" "$mins"
    fi
}

format_countdown_days() {
    local resets_at="$1"
    local now
    now=$(date +%s)
    local diff=$(( resets_at - now ))
    if (( diff <= 0 )); then
        echo "r now"
        return
    fi
    local days=$(( diff / 86400 ))
    if (( days >= 1 )); then
        printf "r in %dd" "$days"
    else
        local hours=$(( diff / 3600 ))
        printf "r in %dh" "$hours"
    fi
}

FIVE_HOUR_PCT=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
FIVE_HOUR_RESETS=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
SEVEN_DAY_PCT=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
SEVEN_DAY_RESETS=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

RATE_LIMITS_LINE=""
if [ -n "$FIVE_HOUR_PCT" ]; then
    FIVE_HOUR_FMT=$(printf "%.0f" "$FIVE_HOUR_PCT")
    FIVE_HOUR_COUNTDOWN=""
    [ -n "$FIVE_HOUR_RESETS" ] && FIVE_HOUR_COUNTDOWN=" ${DIM}($(format_countdown_hours "$FIVE_HOUR_RESETS"))${RESET}"
    RATE_LIMITS_LINE="5h: ${FIVE_HOUR_FMT}%${FIVE_HOUR_COUNTDOWN}"
fi
if [ -n "$SEVEN_DAY_PCT" ]; then
    SEVEN_DAY_FMT=$(printf "%.0f" "$SEVEN_DAY_PCT")
    SEVEN_DAY_COUNTDOWN=""
    [ -n "$SEVEN_DAY_RESETS" ] && SEVEN_DAY_COUNTDOWN=" ${DIM}($(format_countdown_days "$SEVEN_DAY_RESETS"))${RESET}"
    [ -n "$RATE_LIMITS_LINE" ] && RATE_LIMITS_LINE="${RATE_LIMITS_LINE} ${MAGENTA}|${RESET} "
    RATE_LIMITS_LINE="${RATE_LIMITS_LINE}7d: ${SEVEN_DAY_FMT}%${SEVEN_DAY_COUNTDOWN}"
fi

# Effort level from session JSON (reflects current /effort, not settings.json)
EFFORT_LEVEL=$(echo "$input" | jq -r '.effort.level // empty')

# Output style + effort label
EFFORT_LABEL=""
if [ -n "$OUTPUT_STYLE" ] && [ "$OUTPUT_STYLE" != "default" ]; then
    EFFORT_LABEL=" ${MAGENTA}|${RESET} ${CYAN}${OUTPUT_STYLE}${RESET}"
fi
if [ -n "$EFFORT_LEVEL" ]; then
    EFFORT_LABEL="${EFFORT_LABEL} ${MAGENTA}|${RESET} ${CYAN}${EFFORT_LEVEL}${RESET}"
fi

# Line 1: context usage | model | effort
printf "%s\n" "${CTX_COLOR}ctx: ${USED_K}k/${TOTAL_K}k (${REAL_PCT_FMT}%)${RESET} ${MAGENTA}|${RESET} ${YELLOW}${MODEL_NAME}${RESET}${EFFORT_LABEL}"
# Line 2: dir | branch
printf "%s\n" "${BLUE}📁 ${DIR_NAME}${RESET}${GIT_BRANCH}"
# Line 3: rate limits (only if available)
if [ -n "$RATE_LIMITS_LINE" ]; then
    printf "%s\n" "${RATE_LIMITS_LINE}"
fi
