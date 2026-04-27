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

# Resolve which branch to use.
# ccwn strips the prefix (feature/, fix/, ...) and truncates to 64 chars before
# passing the name here. So we reverse the process: for every local branch, apply
# the same strip+truncate and check if it matches NAME.
RESOLVED_BRANCH=""
while IFS= read -r branch; do
    stripped="${branch#*/}"          # strip feature/, fix/, chore/, etc.
    truncated="${stripped:0:64}"
    truncated="${truncated%-}"       # strip trailing dash if mid-word cut
    if [ "$truncated" = "$NAME" ] || [ "$stripped" = "$NAME" ] || [ "$branch" = "$NAME" ]; then
        RESOLVED_BRANCH="$branch"
        break
    fi
done < <(git -C "$CWD" branch --format='%(refname:short)' 2>/dev/null)

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

# Copy .agents/ into the worktree — not tracked by git, contains actual skill files
# that .claude/skills/ symlinks point to via relative paths (../../.agents/skills/...)
if [ -d "$CWD/.agents" ]; then
    cp -r "$CWD/.agents" "$WORKTREE_PATH/.agents" 2>/dev/null || true
    echo "Copied .agents/ contents to worktree" >&2
fi

# Self-heal broken skill symlinks: .claude/skills/<name> is tracked in git (so it's
# always present after clone/checkout), but its target lives in .agents/skills/<name>
# which is gitignored. If the target is ever deleted from the project root, every new
# worktree inherits the broken symlink. Recover by scanning sibling worktrees for the
# missing target, copying it back to root (so future worktrees get it too) and to
# this worktree.
if [ -d "$WORKTREE_PATH/.claude/skills" ]; then
    for link in "$WORKTREE_PATH/.claude/skills"/*; do
        [ -L "$link" ] || continue
        [ -e "$link" ] && continue   # symlink resolves — fine
        name=$(basename "$link")
        for src in "$CWD/.claude/worktrees"/*/.agents/skills/"$name"; do
            [ -d "$src" ] || continue
            mkdir -p "$CWD/.agents/skills/$name" "$WORKTREE_PATH/.agents/skills/$name"
            cp -r "$src"/. "$CWD/.agents/skills/$name/"
            cp -r "$src"/. "$WORKTREE_PATH/.agents/skills/$name/"
            echo "Self-healed missing skill '$name' from $src" >&2
            break
        done
    done
fi

# Copy docs/tickets/ — gitignored so not checked out automatically
if [ -d "$CWD/docs/tickets" ]; then
    cp -r "$CWD/docs/tickets" "$WORKTREE_PATH/docs/tickets" 2>/dev/null || true
    echo "Copied docs/tickets to worktree" >&2

    # Create CURRENT.md symlink pointing to the ticket file for this branch
    TICKET_NUM=$(echo "$NAME" | grep -oiE 'eng-[0-9]+' | head -1 | tr '[:lower:]' '[:upper:]') || true
    if [ -n "$TICKET_NUM" ]; then
        TICKET_FILE="$WORKTREE_PATH/docs/tickets/${TICKET_NUM}.md"
        if [ -f "$TICKET_FILE" ]; then
            ln -sf "${TICKET_NUM}.md" "$WORKTREE_PATH/docs/tickets/CURRENT.md"
            echo "Created CURRENT.md -> ${TICKET_NUM}.md" >&2
        fi
    fi
fi

# Install dependencies in the new worktree (skip if node_modules already exists)
if [ -f "$WORKTREE_PATH/package.json" ] && [ ! -d "$WORKTREE_PATH/node_modules" ]; then
    echo "Running yarn install in worktree..." >&2
    (cd "$WORKTREE_PATH" && yarn install --frozen-lockfile 2>&1 | tail -5) >&2 || true
fi

echo "$WORKTREE_PATH"
