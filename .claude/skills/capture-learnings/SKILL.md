---
name: capture-learnings
description: Use when the user asks to capture or list session learnings, says "qué aprendimos", "listá los aprendizajes", "resumí la sesión", or "qué recordamos de esta sesión".
argument-hint: [tema opcional]
---

## Task

Analyze the current conversation and extract learnings worth remembering in future sessions.

If a focus topic was provided — `$ARGUMENTS` — prioritize learnings related to it without discarding other relevant ones.

### Step 1 — Scan the session

Review the full conversation looking for:
- New commands, configs, tools, or workarounds discovered
- Errors encountered and how they were resolved
- Corrections or feedback the user gave Claude (behavior, approach, preferences)
- Decisions made about the project or workflow
- In-progress work state that would be useful context next session

### Step 2 — Filter duplicates

Cross-reference each candidate learning against the CLAUDE.md and MEMORY.md content already injected above. Discard anything already documented there.

### Step 3 — Present the list

Output a numbered list. For each item include:
- **Qué:** what was learned, concisely and concretely
- **Por qué:** why it's relevant for future sessions
- **Dónde:** where to save it — one of:
  - `CLAUDE.md global` (~/.claude/CLAUDE.md) — permanent instructions, preferences, behaviors
  - `MEMORY.md proyecto` (memory/ in current project) — project-specific context
  - `Skill: <nombre>` — update an existing skill with new behavior

Keep each item short. No fluff.

### Step 4 — Save on user instruction

Present the list and wait. The user will indicate which items to save and where (e.g. "guardá el 1", "guardá todos", "el 2 en CLAUDE.md global").

Save as instructed, confirm con ✓ breve.
