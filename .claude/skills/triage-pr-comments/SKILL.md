---
name: triage-pr-comments
description: Use when reviewing or triaging comments on a GitHub PR.
allowed-tools: Bash(git *), Bash(gh *), Read, Grep, Glob, Edit, Write
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

### Step 2 — Open a worktree for the PR branch

**Before reading any code or applying any fix**, open a dedicated worktree for the PR branch. All file reads and edits must happen inside this worktree — never modify the current branch directly.

The worktree must be created **outside the repo directory** to avoid polluting the working tree and confusing Prettier/lint/test runs:

```bash
# Get repo root first
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")
git worktree add "$HOME/.claude/worktrees/${REPO_NAME}-pr-<PR_NUMBER>-fixes" <PR_BRANCH>
```

Note: `git worktree add` requires `<PR_BRANCH>` to not already be checked out in another worktree. If it is, use `EnterWorktree` to create a new branch based on HEAD and open a PR from that branch into the PR branch.

Do not skip this step even if the fixes look trivial.

### Step 3 — Read the code

For each inline comment: read the file at `~/.claude/worktrees/<REPO_NAME>-pr-<PR_NUMBER>-fixes/<path>` around the indicated line + the `diff_hunk`. For general comments: use PR title, description, and diff as context.

### Step 4 — Output triage report

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

### Step 5 — Wait for user approval before touching any code

**STOP here.** Output the triage report and wait for the user to explicitly confirm which items to fix. Do NOT edit any file, create any commit, or run any write operation until the user says so.

Only proceed to Step 6 after receiving explicit confirmation (e.g. "fix all", "fix #1 and #3", "go ahead").

### Step 6 — Apply fixes and push

For the items the user approved: edit the files inside `~/.claude/worktrees/<REPO_NAME>-pr-<PR_NUMBER>-fixes/`, then commit and push from the worktree:

```bash
cd ~/.claude/worktrees/<REPO_NAME>-pr-<PR_NUMBER>-fixes
git add <files>
git commit -m "<TICKET>: <description>"
```

Group related fixes into a single commit when possible.

### Step 6b — Validate before pushing

From the worktree, run CI checks on the changed files before pushing:

```bash
cd .claude/worktrees/pr-<PR_NUMBER>-fixes
git diff --name-only --relative origin/master HEAD | xargs yarn lint
yarn typecheck
```

Fix any failures before proceeding. Only push once both pass.

```bash
git push
```

### Step 7 — Wait for user confirmation, then clean up

Do NOT remove the worktree until the user explicitly confirms they have reviewed the pushed changes.

```bash
git worktree remove ~/.claude/worktrees/<REPO_NAME>-pr-<PR_NUMBER>-fixes
```
