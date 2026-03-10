---
name: create-skill
description: Use when creating or editing a Claude Code skill (SKILL.md).
---

# Create Skill

## Frontmatter

```yaml
---
name: skill-name          # letters, numbers, hyphens only
description: Use when ... # triggering conditions ONLY — never summarize the workflow
context: fork             # optional: runs skill in isolated context
agent: general-purpose    # optional: spawns subagent
allowed-tools: Bash(git *), Read, Edit, Write   # optional: restrict tools
argument-hint: [arg]      # optional: hint shown in autocomplete
---
```

**`disable-model-invocation: true`** — only add this if you want the skill to run exclusively via `/skill-name`. Without it, Claude auto-triggers based on the description.

## Description rules

- Start with `"Use when..."` — triggering conditions only
- **Never summarize the workflow** — Claude may follow the description instead of reading the skill body
- Keep it short; once auto-trigger works, simplify further

```yaml
# ❌ Bad — summarizes workflow
description: Use when reviewing PRs — creates worktree, reads comments, outputs Fix/Skip table.

# ✅ Good — triggering condition only
description: Use when reviewing or triaging comments on a GitHub PR.
```

## Structure

```markdown
## Context          ← injected vars (!`command`, $ARGUMENTS)
## Task             ← what the agent does
### Step N          ← numbered steps, concise
```

Keep steps action-oriented. Inline bash blocks only when the command is non-obvious.