---
name: warp-agent
description: Use when the user asks to open a coding agent CLI (Claude Code / cc, opencode, or codex) in a Warp tab or pane — e.g. "abrime opencode para retomar el handoff", "lanzá codex en una tab nueva", "open warp with cc and this prompt".
argument-hint: 'agent + worktree + prompt'
---

## Context

Three CLIs are supported. Each is a zsh function or installed binary:

| Agent | Invocation | Model flag | Effort flag |
|---|---|---|---|
| **cc** (Claude Code) | `ccwt [--model M] [--effort E] <worktree> "<prompt>"` | `--model sonnet\|opus\|haiku` | `--effort low\|medium\|high\|xhigh\|max` |
| **opencode** | `cd <worktree-dir> && opencode -m <provider/model> --prompt "<prompt>"` | `-m <provider/model>` — prefer `openai/*` over `github-copilot/*` (e.g. `openai/gpt-5.4`); list with `opencode models` | not exposed via CLI flag |
| **codex** | `cd <worktree-dir> && codex -m <model> -c model_reasoning_effort=<E> "<prompt>"` | `-m <model>` (e.g. `gpt-5.5`) | `-c model_reasoning_effort=low\|medium\|high` |

Notes:
- `ccwt` resolves a worktree by branch name and forwards `--model`/`--effort` to `cc`. For `opencode`/`codex` there is no `*wt` wrapper — `cd` to the worktree dir manually.
- Worktrees live at `<repo>/.claude/worktrees/<name>/`. To resolve from a branch: `git -C <repo> worktree list --porcelain`.
- For Lift specifically: repo at `~/dev/rabbet/lift`, worktrees at `~/dev/rabbet/lift/.claude/worktrees/`.

## Task

### Step 1 — Gather inputs

Extract from the user's request (ask only what's missing):

1. **Agent**: cc | opencode | codex
2. **Worktree** or branch name (or absolute dir if not a worktree)
3. **Prompt** (the initial message — may be a path like "Lee handoff.md y …")
4. **Model + effort**: **default to `--model sonnet --effort high` for `cc`**, always. Only override if the user explicitly says otherwise (e.g. "usá opus", "con effort max", "sonnet medium"). Do not ask — just pass `--model sonnet --effort high` unless the user named another combination. The parent agent's current model is irrelevant; never inherit it.

Do not invent model names. If the user says "GPT-5" or similar shorthand, run `opencode models` (for opencode) or check `~/.codex/config.toml` (for codex) to map to a real id.

### Step 2 — Surface: split-right by default

**Always split-right in the current Warp window. Do not ask.** Only deviate if the user explicitly says "tab nueva" / "abajo" / "split down" in the original request.

### Step 3 — Build the command string

Resolve the absolute worktree directory first. Then compose:

- **cc**: `ccwt [--model M] [--effort E] <worktree-name> "<prompt>"` — `cd` is handled by ccwt itself.
- **opencode**: `cd <abs-dir> && opencode -m <model> --prompt "<prompt>"` (use `--prompt` for non-interactive seed; interactive UI follows).
- **codex**: `cd <abs-dir> && codex -m <model> -c model_reasoning_effort=<E> "<prompt>"`. Omit `-m` and `-c` flags to use defaults from `~/.codex/config.toml`.

Escape double quotes inside the prompt (`\"`).

**Always prefix opencode/codex with `cd <abs-dir> && ` — even for pane splits.** The split inherits cwd from the parent pane, but if the parent isn't in the worktree (or you're opening a tab), relative paths in the prompt (e.g. `docs/tickets/.../handoff.md`) will fail silently. `cd` is idempotent and cheap.

### Step 4 — Launch

**Tab nueva**: invoke the `warp-tab` skill with:
- directory = absolute worktree dir
- command = the full string from Step 3

`warp-tab` handles the `xdg-open` + `sleep 2` + `xdotool` recipe.

**Pane split** (in the currently-focused Warp window):

```bash
# Ctrl+Shift+D = split right · Ctrl+Shift+E = split down
# --delay 60 is required: default xdotool typing speed drops chars in Warp
xdotool key ctrl+shift+d && sleep 1.5 && \
  xdotool type --clearmodifiers --delay 60 '<command>' && xdotool key Return
```

The new pane inherits the parent pane's cwd, so for `cc` you can skip `ccwt` and call `cc --model M --effort E "prompt"` directly when the parent is already in the right worktree.

### Step 5 — Confirm with the user

After launching, ask whether the agent started correctly. If it didn't (focus issue, command typed in wrong pane), retry with longer `sleep` or fall back to the other surface.

## Troubleshooting

- **`xdotool type` drops chars in Warp** (e.g. `Lee docs` → `Leedocs`, `ENG-4602` → `ENg-4602`). Cause: default delay (12 ms) is too fast for Warp's input handling on Wayland/XWayland. Fix: always pass `--delay 60`. Tested working on a long mixed-case prompt with quotes and accents.
- **Don't fall back to clipboard paste** (`wl-copy` + `Ctrl+V`). It pollutes the user's clipboard and Warp's paste shortcut isn't always `Ctrl+V` (varies by config). `xdotool type --delay 60` is the right fix.
- **Pane focus race**: the new split needs ~1.5 s before it accepts keystrokes. Using `sleep 1` causes the first chars to land in the wrong pane.
- **Always `cd <abs-dir> && ` for opencode/codex**, even on pane splits. The split inherits the parent cwd, but if the user invokes the skill from a tab that isn't already in the worktree (or asks for a brand-new tab), relative paths in the prompt fail silently.
- **Opencode model providers**: `opencode models` lists both `github-copilot/*` and `openai/*` for the same model id. Default to `openai/*` unless the user explicitly says otherwise — github-copilot routing has caused confusion.
- **Codex + asdf node version mismatch**: `codex` is installed under a specific node version (npm-global). When `cd`-ing into a project whose `.tool-versions` pins a different node, the asdf shim resolves to the project's node and `codex` is missing. Symptom: `codex: command not found` or "no version is set" error. Workaround: prefix with `ASDF_NODEJS_VERSION=<installed-version> codex …`. To find the right version: `for v in ~/.asdf/installs/nodejs/*/bin/codex; do echo "$v"; done`. Permanent fix (do not run without user consent): `npm i -g @openai/codex` under the project's pinned node version.
- **Long prompts → write to a file, don't type them inline**: if the prompt has more than ~1 line, or contains backticks, double quotes, dollar signs, or any markdown formatting, `Write` it to `/tmp/<task>-prompt.txt` and have xdotool type `cc --model M --effort E "$(cat /tmp/<task>-prompt.txt)"` (or `ccwt …` variant). Inline typing forces double-layer escaping (shell + xdotool keystroke timing) that silently mangles backticks and quotes, even with `--delay 60`. The `$(cat …)` substitution runs once in the target pane's shell and preserves the file content as a single argument — no escape gymnastics. Only inline short prompts (1 sentence, no special chars).
