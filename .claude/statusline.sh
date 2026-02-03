#!/bin/bash
# Force C locale for numeric formatting
export LC_NUMERIC=C

# Read JSON input from stdin
input=$(cat)

# Extract values
PERCENT_USED=$(echo "$input" | jq -r '.context_window.used_percentage // 0')
MODEL_NAME=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir')
DIR_NAME=$(basename "$CURRENT_DIR")

# Get git branch if in a git repo
GIT_BRANCH=""
if git -C "$CURRENT_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git -C "$CURRENT_DIR" branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        GIT_BRANCH=" \033[35m|\033[0m \033[36m$BRANCH\033[0m"
    fi
fi

# Format percentage with color (red if >80%, yellow if >60%, green otherwise)
if (( $(echo "$PERCENT_USED > 80" | bc -l) )); then
    COLOR="\033[31m"  # Red
elif (( $(echo "$PERCENT_USED > 60" | bc -l) )); then
    COLOR="\033[33m"  # Yellow
else
    COLOR="\033[32m"  # Green
fi

# Format percentage
PERCENT_FORMATTED=$(printf "%.1f" "$PERCENT_USED")

# Output formatted status line using echo -e to properly render ANSI codes
echo -e "${COLOR}${PERCENT_FORMATTED}%\033[0m \033[35m|\033[0m \033[33m${MODEL_NAME}\033[0m \033[35m|\033[0m \033[34m📁 ${DIR_NAME}\033[0m${GIT_BRANCH}"
