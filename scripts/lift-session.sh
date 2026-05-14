#!/usr/bin/env bash
# Tmux sessionizer for the Lift dev environment.
# Creates a session with three windows: backend (docker compose), frontend (vite :3004), shell.
# If the session already exists, re-attaches to it.

SESSION="lift"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux attach -t "$SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -n "backend" -c ~/dev/rabbet/dozer
tmux send-keys -t "$SESSION:backend" "docker compose up" Enter

tmux new-window -t "$SESSION" -n "frontend" -c ~/dev/rabbet/lift
tmux send-keys -t "$SESSION:frontend" "yarn start --port 3004" Enter

tmux new-window -t "$SESSION" -n "shell" -c ~/dev/rabbet/lift

tmux select-window -t "$SESSION:shell"
tmux attach -t "$SESSION"
