#!/usr/bin/env bash
# Tmux sessionizer for the Ticketo dev environment.
# Creates a session with two windows: dev (backend :5181 + frontend Vite :5180), shell.
# If the session already exists, re-attaches to it.

SESSION="ticketo"
ROOT="$HOME/personal/ticketo"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux attach -t "$SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -n "dev" -c "$ROOT"
tmux send-keys -t "$SESSION:dev" "bash scripts/dev.sh" Enter

tmux new-window -t "$SESSION" -n "shell" -c "$ROOT"

tmux select-window -t "$SESSION:shell"
tmux attach -t "$SESSION"
