---
name: triage-pr-comments
description: Use when the user asks to review, check, triage, or analyze comments on a GitHub PR — including when they share a PR URL and ask about its review comments or what to fix.
context: fork
agent: general-purpose
allowed-tools: Bash(git *), Bash(gh *), Read, Grep, Glob
argument-hint: [pr-url|branch-name|pr-number]
---

## Context

Argument: **$ARGUMENTS** | Branch: !`git branch --show-current`

## Task

Senior engineer triaging PR review comments. Produce a **Fix** / **Skip** verdict per comment, grounded in the actual code.

### Step 1 — Resolve the PR

- Branch name (has `/`, no `github.com`): `gh pr list --head <branch> --json number,headRefName,baseRefName --limit 1`
- URL, number, or empty: `gh pr view $ARGUMENTS --json number,headRefName,baseRefName`

Fetch inline comments (owner/repo from `gh repo view --json owner,name`):

```bash
gh api "repos/{owner}/{repo}/pulls/<PR_NUMBER>/comments" \
  --jq '[.[] | {id, path, line: (.line // .original_line), body, user: .user.login, diff_hunk}]'
```

### Step 2 — Read the code

```bash
git worktree remove --force .claude/worktrees/pr-<PR_NUMBER> 2>/dev/null || true
git worktree add .claude/worktrees/pr-<PR_NUMBER> <HEAD_BRANCH>
```

For each inline comment: read the file at `.claude/worktrees/pr-<PR_NUMBER>/<path>` around the indicated line + the `diff_hunk`. For general comments: use PR title, description, and diff as context.

### Step 3 — Output triage report

```
## PR #<number> — Comment Triage

### Inline comments (<count> total, grouped by unique concern)

| # | File:Line | Author | Comment (excerpt) | Verdict | Reasoning |
|---|-----------|--------|-------------------|---------|-----------|

### General comments (<count>)

| # | Author | Comment (excerpt) | Verdict | Reasoning |
|---|--------|-------------------|---------|-----------|

### Summary
- **Fix** (X): #1, #3, ...
- **Skip** (Y): #2, #4, ...

**Quick reference for fixes:**
| # | What to do |
|---|------------|
```

**✅ Fix:** real bug / null-deref · security or data integrity risk · missing coverage for non-trivial path · naming inconsistency that breaks callers or violates established conventions · valid a11y concern · wrong/unsafe type · behavior regression.

**❌ Skip:** pure style preference · out-of-scope refactor · concern already addressed in current code · factually wrong (explain why) · over-engineering · convention not present in this codebase · cosmetic.

Borderline → default ✅ Fix, note the trade-off. Factually wrong → explain the reviewer's misunderstanding.

### Step 4 — Clean up worktree

```bash
git worktree remove --force .claude/worktrees/pr-<PR_NUMBER>
```

> **Before implementing fixes:** open a dedicated worktree (`EnterWorktree`) — never commit or push from the current branch. Do not remove the fix worktree until the user explicitly confirms.
