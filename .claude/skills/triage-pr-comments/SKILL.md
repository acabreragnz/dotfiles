---
name: triage-pr-comments
description: Use when deciding which PR review comments are worth fixing. Given a PR URL, branch name, PR number, or no argument (uses current branch), creates a git worktree for the PR branch, reads all inline and general review comments in context, and outputs a Fix / Skip verdict with reasoning for each.
disable-model-invocation: true
context: fork
agent: general-purpose
allowed-tools: Bash(git *), Bash(gh *), Read, Grep, Glob
argument-hint: [pr-url|branch-name|pr-number]
---

## Injected context

Argument received: **$ARGUMENTS**

- Current branch: !`git branch --show-current`

## Your task

You are a senior engineer triaging code review comments on a PR. For each comment, produce a clear **Fix** or **Skip** verdict with reasoning grounded in the actual code.

### Step 1 — Resolve the PR

Parse `$ARGUMENTS` to determine which PR to triage. **ALWAYS re-fetch PR data using `gh` — never rely on injected metadata for a specific PR.**

- **If `$ARGUMENTS` is a branch name** (contains `/` but not `github.com`): `gh pr list --head <branch> --json number,title,url,headRefName,baseRefName,state --limit 1`
- **Otherwise** (URL, plain number, or empty): `gh pr view $ARGUMENTS --json number,title,url,headRefName,baseRefName,state` — `gh` handles URLs and numbers natively; omit the argument if empty to use the current branch.

Then fetch comments and diff for the resolved PR:
```bash
gh pr view <PR_NUMBER> --comments
gh pr diff <PR_NUMBER> --name-only
```

Extract and remember: `PR_NUMBER` and `HEAD_BRANCH`.

### Step 2 — Fetch inline review comments

Get the structured inline comments (with file path, line, and diff hunk):

```bash
gh api "repos/{owner}/{repo}/pulls/<PR_NUMBER>/comments" \
  --jq '[.[] | {id, path, line: (.line // .original_line), side, body, user: .user.login, diff_hunk}]'
```

To get `{owner}` and `{repo}`:

```bash
gh repo view --json owner,name --jq '"repos/\(.owner.login)/\(.name)"'
```

### Step 3 — Create a git worktree

Create an isolated worktree for the PR branch so you can read the exact code being reviewed:

```bash
# Remove stale worktree if it exists
git worktree remove --force .claude/worktrees/pr-<PR_NUMBER> 2>/dev/null || true

# Create fresh worktree
git worktree add .claude/worktrees/pr-<PR_NUMBER> <HEAD_BRANCH>
```

### Step 4 — Analyze each comment

For every **inline comment**:
1. Read the file at `.claude/worktrees/pr-<PR_NUMBER>/<path>` around the indicated line
2. Read the `diff_hunk` to understand what changed
3. Determine: does the comment point to a real issue in the code as it stands right now?

For every **general PR comment** (not tied to a line):
1. Read the PR title, description, and diff as context
2. Determine: does this raise a valid concern about the PR overall?

### Step 5 — Output triage report

Produce the following structured report:

```
## PR #<number> — Comment Triage

### Inline comments (<count>)

| # | File:Line | Author | Comment (excerpt) | Verdict | Reasoning |
|---|-----------|--------|-------------------|---------|-----------|
| 1 | src/foo.ts:42 | alice | "rename this to..." | ❌ Skip | Pure naming preference — no functional difference, callers are unaffected, no project convention violated. |
| 2 | src/bar.ts:88 | bob | "this will throw if..." | ✅ Fix | Valid null-dereference risk at a system boundary where the value can genuinely be undefined. |

### General comments (<count>)

| # | Author | Comment (excerpt) | Verdict | Reasoning |
|---|--------|-------------------|---------|-----------|
| 1 | carol | "should we add tests for..." | ✅ Fix | The described edge case has no test coverage and the code path is non-trivial. |

### Summary
- **Total comments**: N
- **Fix** (X): #1, #3, ...
- **Skip** (Y): #2, #4, ...
```

**Verdict criteria**

✅ **Fix** when the comment:
- Catches a real bug, logic error, or null/undefined dereference
- Identifies a security or data integrity risk
- Points to missing test coverage for a non-trivial path
- Highlights a naming or API inconsistency that breaks callers or diverges from established codebase conventions (not personal preference)
- Raises a valid accessibility concern
- Correctly notes that a type annotation is wrong or unsafe
- Points out a behavior regression compared to the pre-PR baseline

❌ **Skip** when the comment:
- Is a pure style preference with no correctness impact ("I'd call it X instead")
- Asks for refactoring that is out of scope for this PR
- Describes a concern that is already addressed in the current code (outdated comment)
- Is factually wrong (reviewer misread or misunderstood the code — explain why)
- Requests over-engineering for hypothetical future requirements
- Applies a convention that does not exist in this codebase
- Is cosmetic only (whitespace, formatting already handled by Prettier/linter)

When a comment is **borderline**, default to ✅ Fix and note the trade-off in the reasoning. When a comment is factually wrong, include a short explanation of why the reviewer's understanding is incorrect.

### Step 6 — Clean up

```bash
git worktree remove --force .claude/worktrees/pr-<PR_NUMBER>
```

### Step 7 — Remind about fix workflow

After outputting the triage report, always append this note:

> **Next step:** To implement the fixes, create a dedicated worktree from the PR branch — never commit or push fix work from the current branch. Use `EnterWorktree` or `git worktree add` on a new branch based on `<HEAD_BRANCH>` before making any changes. All commits and pushes must happen from inside that worktree. **Do not remove the worktree until the user explicitly confirms it's safe to do so — cleanup is always the last step.**
