---
name: warp-tab
description: Use when the user asks to open a Warp terminal tab — with or without a command to run, at a specific directory or worktree.
argument-hint: 'directorio o worktree a abrir'
---

## Context

- Warp binary: `/usr/bin/warp-terminal` → `/opt/warpdotdev/warp-terminal/warp` (Oz CLI — not the GUI launcher)
- GUI is opened via `warp://` URI scheme handled by xdg-open
- `ccwt` and `cc` are zsh shell functions — not standalone binaries
- Tab configs live in `~/.local/share/warp-terminal/tab_configs/` (Linux path)

## Task

Open a new Warp tab at the requested directory, optionally running a command.

### Step 1 — Open the tab and run command (single Bash call)

Always combine into one command — two separate calls cause xdotool to fire before the tab has focus:

```bash
xdg-open "warp://action/new_tab?path=<absolute-dir>" 2>/dev/null & sleep 2 && xdotool type --clearmodifiers "<command>" && xdotool key Return
```

If no command is needed, just open the tab:

```bash
xdg-open "warp://action/new_tab?path=<absolute-dir>" 2>/dev/null
```

### Notes on what works and what doesn't

- ✅ `warp://action/new_tab?path=<dir>` — opens a tab at that directory
- ✅ `warp://action/new_window?path=<dir>` — opens a new window
- ❌ `command=` / `cmd=` URL params — ignored, not supported
- ❌ `warp://action/launch_tab_config?name=<name>` — not officially supported (feature request), unreliable
- ✅ xdotool after sleep 2 — only reliable way to auto-run a command
- For worktrees: directory = worktree path, command = `ccwt <worktree-name>`
- `ccwt` is a zsh function — MUST be typed into the tab via xdotool, not run from Bash directly

## Tab Config Format (for persistent tabs via + menu)

Tab configs in `~/.local/share/warp-terminal/tab_configs/<name>.toml` appear in the Warp `+` menu.
They can't be opened programmatically yet (use xdotool approach above for that).

```toml
name = "Dev Server"
color = "#4A90E2"     # optional hex color

[[panes]]
id = "main"
type = "terminal"     # "terminal" | "agent" | "cloud"
is_focused = true
directory = "~/projects/myapp"
commands = ["yarn start --port 3001"]
```

**Split pane layout:**
```toml
name = "Split"

[[panes]]
split = "horizontal"   # "horizontal" (left/right) | "vertical" (top/bottom)

[[panes]]
id = "editor"
type = "terminal"
directory = "~/myapp"
is_focused = true

[[panes]]
id = "server"
type = "terminal"
directory = "~/myapp"
commands = ["yarn start --port 3001"]
```

**Parameterized tab (prompts user at open time):**
```toml
name = "Branch Worktree"

[[panes]]
id = "main"
type = "terminal"
directory = "{{repo}}"
commands = ["ccwt {{branch}}"]

[params.repo]
type = "repo"
description = "Repository"

[params.branch]
type = "branch"
description = "Branch to open"
```

## Troubleshooting

- **Tab opened but empty (no command ran):** xdotool fired too early — increase `sleep` before xdotool call
- **xdg-open does nothing:** Warp GUI must already be running; the URI scheme only works if the app is open
- **Tab config not appearing in + menu:** check filename is snake_case `.toml` and lives in `~/.local/share/warp-terminal/tab_configs/`
- **Long commands / multi-line prompts → write to a file, don't type them inline:** if the command is more than ~1 line or contains backticks, double quotes, dollar signs, or markdown, `Write` it to `/tmp/<task>-prompt.txt` and pass `cc "$(cat /tmp/<task>-prompt.txt)"` (or `ccwt …`) as the xdotool-typed command. The `$(cat …)` substitution runs once in the new tab's shell and preserves the file content verbatim as a single argument. Typing the full prompt inline forces double-layer escaping (xdotool keystrokes + bash double quotes) that silently mangles content even with `--delay 60`. Reserve inline for short one-shot commands without special chars.
