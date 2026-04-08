#!/bin/bash
set -euo pipefail

# =============================================================================
# Claude Code WorktreeCreate Hook
# =============================================================================
# Overrides the default worktree creation. Creates the git worktree,
# copies .claude/ contents (excluding worktrees/), and outputs the path.
#
# Hook input (JSON via stdin):
#   { "name": "<worktree-name>", "cwd": "<project-root>" }
#
# Hook output (stdout):
#   Absolute path to the worktree directory (consumed by Claude Code)
# =============================================================================

INPUT=$(cat)
NAME=$(echo "$INPUT" | jq -r '.name')
CWD=$(echo "$INPUT" | jq -r '.cwd')

WORKTREE_PATH="$CWD/.claude/worktrees/$NAME"

# Re-entry: worktree already exists
if [ -f "$WORKTREE_PATH/.git" ] || [ -d "$WORKTREE_PATH/.git" ]; then
    echo "Re-entering existing worktree: $WORKTREE_PATH" >&2
    echo "$WORKTREE_PATH"
    exit 0
fi

mkdir -p "$CWD/.claude/worktrees"

# Resolve which branch to use:
# 1. Exact match
# 2. Common prefix matches (feature/, fix/, chore/, docs/, test/, backup/)
# 3. Fall back to creating a new worktree-$NAME branch from origin/master
RESOLVED_BRANCH=""
for candidate in "$NAME" "feature/$NAME" "fix/$NAME" "chore/$NAME" "docs/$NAME" "test/$NAME" "backup/$NAME"; do
    if git -C "$CWD" show-ref --verify --quiet "refs/heads/$candidate" 2>/dev/null; then
        RESOLVED_BRANCH="$candidate"
        break
    fi
done

if [ -n "$RESOLVED_BRANCH" ]; then
    echo "Checking out existing branch: $RESOLVED_BRANCH" >&2
    git -C "$CWD" worktree add "$WORKTREE_PATH" "$RESOLVED_BRANCH" >&2
else
    DEFAULT_BRANCH=$(git -C "$CWD" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo "master")
    BASE_REF="origin/$DEFAULT_BRANCH"
    BRANCH_NAME="worktree-$NAME"
    echo "Creating new branch: $BRANCH_NAME from $BASE_REF" >&2
    if git -C "$CWD" show-ref --verify --quiet "refs/heads/$BRANCH_NAME" 2>/dev/null; then
        git -C "$CWD" worktree add "$WORKTREE_PATH" "$BRANCH_NAME" >&2
    else
        git -C "$CWD" worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" "$BASE_REF" >&2
    fi
fi

# Copy .claude/ contents into the worktree (skip worktrees/ and settings.local.json)
if [ -d "$CWD/.claude" ]; then
    mkdir -p "$WORKTREE_PATH/.claude"
    for f in "$CWD/.claude"/*; do
        base=$(basename "$f")
        [ "$base" = "worktrees" ] && continue
        [ "$base" = "settings.local.json" ] && continue
        cp -r "$f" "$WORKTREE_PATH/.claude/" 2>/dev/null || true
    done
    echo "Copied .claude/ contents to worktree" >&2
fi

echo "$WORKTREE_PATH"
