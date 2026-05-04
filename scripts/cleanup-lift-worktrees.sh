#!/bin/bash
set -euo pipefail

LIFT_DIR="/home/tcabrera/dev/rabbet/lift"
WORKTREES_DIR="$LIFT_DIR/.claude/worktrees"
MAX_DAYS="${1:-5}"
ALWAYS_KEEP=("master")

cd "$LIFT_DIR"
git fetch origin master --quiet 2>/dev/null || true

git worktree list --porcelain \
  | awk '/^worktree /{wt=$2} /^branch /{print wt, $2}' \
  | while read -r worktree_path branch_ref; do
    branch="${branch_ref#refs/heads/}"

    # Skip main worktree and anything outside .claude/worktrees/
    [[ "$worktree_path" == "$LIFT_DIR" ]] && continue
    [[ "$worktree_path" != "$WORKTREES_DIR/"* ]] && continue

    # Skip always-keep branches
    for keep in "${ALWAYS_KEEP[@]}"; do
      [[ "$branch" == "$keep" ]] && continue 2
    done

    # Skip worktrees with real uncommitted changes.
    # Ignore noise: untracked .claude/ and .agents/ (Claude session files),
    # and auto-generated src/__generated__/graphql.ts (never committed).
    real_dirty=$(git -C "$worktree_path" status --porcelain 2>/dev/null \
      | grep -v '^?? \.claude/' \
      | grep -v '^?? \.agents' \
      | grep -v ' M src/__generated__/graphql\.ts' \
      || true)
    if [[ -n "$real_dirty" ]]; then
      echo "SKIP (dirty): $branch"
      continue
    fi

    # Compute age in days from last commit on the branch
    last_commit_ts=$(git log -1 --format="%ct" "$branch" 2>/dev/null || echo 0)
    now=$(date +%s)
    age_days=$(( (now - last_commit_ts) / 86400 ))

    if [[ "$age_days" -ge "$MAX_DAYS" ]]; then
      echo "REMOVE ($age_days days old): $worktree_path  [$branch]"
      git worktree remove --force "$worktree_path" 2>/dev/null || true
      git branch -D "$branch" 2>/dev/null || true
    else
      echo "keep   ($age_days days old): $branch"
    fi
  done

# Prune stale worktree metadata
git worktree prune
