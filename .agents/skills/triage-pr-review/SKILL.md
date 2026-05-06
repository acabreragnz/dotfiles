---
name: triage-pr-review
description: Use when scoring or triaging files on a large branch/PR to decide which to self-review and which to delegate to automated review agents.
allowed-tools: Bash(git *), Bash(gh *), Bash(python3 *), Bash(mkdir *), Bash(cat *), Bash(ls *), Bash(rg *), Read, Write, Edit, Task
argument-hint: 'componente o patrón target opcional (ej: Paragraph)'
---

## Context

Argument: **$ARGUMENTS** | Branch: !`git branch --show-current` | Default base: master

## Task

Triage every modified file on the current branch into 4 risk buckets (DEEP / REVIEW / SCAN / SKIP), then dispatch parallel review agents per bucket and produce a self-review checklist for the human author.

The risk dimensions are **derived on the fly** for each branch — there is no fixed scoring formula. The skill always pauses for explicit user approval before generating the script.

### Step 1 — Understand the branch (delegated)

Spawn a `general-purpose` subagent with this prompt (substitute `<TARGET>` with `$ARGUMENTS` if provided, otherwise omit):

```
Read these in order and return a structured brief in <400 words:

1. docs/tickets/CURRENT.md (if present) — ticket scope
2. The open draft PR body for this branch: `gh pr view --json title,body --jq '.title, .body'`
3. Full diff against master: `git diff master...HEAD --stat` and a sample of `git diff master...HEAD -- <top 10 files by churn>`

Return:
A. INTENT — feature / refactor / migration / fix; target component or API (<TARGET> if specified)
B. CHANGE CATEGORIES — list each kind of change present (e.g. "import-only swap", "prop signature change", "structural JSX rewrite", "test scaffolding"), with rough file counts
C. CRITICAL PATHS — which directories in this branch carry production weight (pages, materials, etc.)
D. RED FLAGS — oxlint-disable additions, scope creep (mixing unrelated features), missing tests for risky changes, anything else worth weighting

Plain text. No code blocks except for paths. No recommendations — just the brief.
```

Wait for the subagent's brief before continuing.

### Step 2 — Propose risk dimensions (loop until approved)

Using the brief from Step 1, propose A/B/C/D dimensions in chat as a markdown table. **Skeleton is fixed; contents are derived.**

- **A. Naturaleza del cambio** — categories specific to this branch (e.g. `A0` import-only = 0, `A4` structural JSX = 4). Pull from the brief's CHANGE CATEGORIES.
- **B. Superficie del diff** — `floor(LOC_outside_imports / 10)` capped at 4.
- **C. Criticidad del archivo** — path-based scoring derived from CRITICAL PATHS (e.g. `pages/<critical>/**` = 3, `*.stories.*` / `*.test.*` = 0, target component itself = 5).
- **D. Señales colaterales** — RED FLAGS from the brief, each +1.

Also propose bucket thresholds (e.g. `0 → SKIP, 1-2 → SCAN, 3-5 → REVIEW, ≥6 → DEEP`) and a human-readable rationale.

**Wait for explicit approval.** If the user critiques (weights, dimensions, paths), revise and re-propose. Loop until they say "ok" / "dale" / "go ahead".

### Step 3 — Generate one-shot triage script

Write `/tmp/triage-<branch-slug>.py` with everything embedded (no imports from `.agents/`). **Delegate this step to a Sonnet subagent** (`Agent` with `subagent_type: general-purpose`, `model: sonnet`) — the script is mechanical and the parent context shouldn't burn tokens on it.

The script must use a **hybrid approach**: ast-grep for structural detections, regex on diff hunks for line-based metrics.

#### Structural detections — use ast-grep on full files

Diff hunks aren't valid JSX/TSX (they're partial), so ast-grep can't parse them. Instead, for each modified file: snapshot master via `git show master:<path> > /tmp/triage-master-<sanitized>.<ext>` and run ast-grep on both the master snapshot AND the current working-tree file. Compare match counts to detect what was *introduced*.

Use ast-grep for:
- **Target component JSX presence** (e.g. `<Paragraph $$$></Paragraph>` and self-closing variant) — drives D4 (no-target-touch flag) and is a precondition for A1+
- **Wrapping/structural patterns** (e.g. `<Pane>...<Paragraph>...</Pane>` introduced) — drives A4
- **Attribute-value changes inside the target** (e.g. `<Paragraph color=$VAL>` with `$VAL` matching `#hex` or `theme.`) — drives A3
- **className containing layout utilities** inside the target — drives A2

Required ast-grep flags: scan with both `--lang tsx` and `--lang jsx` (no automatic fallback in mixed codebases); always `stopBy: end` on relational rules; use `--ignore` for test/story exclusions, not Python post-filtering. See the `/ast-grep` skill for syntax.

#### Line-based detections — use regex on diff hunks

For these, regex on `git diff master...HEAD -- <file>` is fine:
- **B (LOC outside imports)** — count `+` lines not matching `^[+]\s*(import|from)\s`
- **D1 (oxlint-disable added)** — `+` line contains `oxlint-disable`
- **D2 (scope creep hygiene)** — `+` line with `void <ident>(`, OR `.flatMap(` added with `.reduce(` removed
- **D5 (trailing whitespace introduced)** — `+` line matches `\S+ +$`

#### Outputs

`.agents/review-buckets-{deep,review,scan,skip}.txt` (one path per line) and `.agents/review-triage-summary.txt` (counts + score histogram + top-30 table with score breakdown per file). Run from repo root: `python3 /tmp/triage-<branch-slug>.py`.

### Step 4 — Sanity check for scope creep

If `$ARGUMENTS` named a target component or pattern, audit the DEEP bucket: for each file, check whether its diff actually touches that target. Report files that don't (likely scope creep from another feature). Wait for the user to filter or confirm before Step 5.

If no target was given, skip this step.

### Step 5 — Generate self-review checklist

Write `.agents/self-review-list.md`: markdown checklist of every file with score ≥ 4 (the SCAN/REVIEW/DEEP bucket files), sorted by score descending. Each line:

```
- [ ] `<path>` _(score N)_
```

Add a header noting total count and the score threshold used.

### Step 6 — Phase 2: dispatch review agents

For each bucket, spawn agents in **background** (`run_in_background: true`):

| Bucket | Agent strategy |
|---|---|
| SKIP | none |
| SCAN | 1 `general-purpose` agent, full bucket as input, prompt: "glance at each file's diff, report only surprises in <2 lines per file" |
| REVIEW | N `pr-review-toolkit:code-reviewer` agents, 3-5 files per agent, prompt: focused review against the dimensions from Step 2 |
| DEEP | 1 `pr-review-toolkit:code-reviewer` agent per file, prompt: detailed review with the file's specific red flags from the triage script |

Each agent is told to return findings in a structured format (file:line / severity / message). Pass the relevant `git diff master...HEAD -- <file>` inline in the prompt — do not let the agent re-fetch it.

### Step 7 — Consolidate findings

When all background agents finish, merge their outputs into `.agents/review-report.md`:

- Group by file path
- Sort by max severity within file, then by score from triage
- Each finding: `**file:line** — severity — message`

### Step 8 — Final summary in chat

Print a compact summary:

```
📊 Triage complete (<total> files)
   DEEP=<n> · REVIEW=<n> · SCAN=<n> · SKIP=<n>

🚨 Scope creep: <n> files in DEEP don't touch <TARGET> — see review-buckets-deep.txt
✅ Self-review checklist: .agents/self-review-list.md (<n> files, threshold score ≥ 4)
🤖 Phase 2 review: .agents/review-report.md (<n> findings across <n> files)
```

Omit the scope-creep line if Step 4 was skipped or returned zero hits.

## Notes

- **Always pause before Step 3.** The user explicitly wants to approve dimensions and weights before any code is generated. Never skip Step 2's loop.
- **Buckets go in `.agents/`** (project-local, can be committed if useful, gitignored otherwise). Script goes in `/tmp/` (one-shot, not reusable across branches because dimensions differ).
- **Phase 2 runs in background.** Continue conversation while agents work; results come in via completion notifications.

## Troubleshooting

### Master snapshot — preserve file extension

When dumping `git show master:<path>` to a temp file for ast-grep, **only sanitize `/` separators, never the file extension**. ast-grep relies on the extension to pick the parser; a snapshot named `src_pages_X.txt` (or just `src_pages_X` with no extension) fails silently with zero matches even though the file content is valid JSX/TSX.

```python
# ✅ correct
snapshot = f"/tmp/triage-master-{path.replace('/', '_')}"  # extension preserved

# ❌ wrong — strips the extension
snapshot = f"/tmp/triage-master-{path.replace('.', '_').replace('/', '_')}"
```

If you see v2 producing wildly inflated A=4 counts (110+ structural detections), check the master snapshot filenames first — that's the signature.

### Phase 2 agents — pre-fetch diff inline, never let them call `git diff`

`pr-review-toolkit:code-reviewer` agents launched with just a file path and an instruction "run `git diff master...HEAD -- <file>`" will sometimes return false "OK" / "no diff" results — the sub-shell appears to misfire and the agent reports a clean file when it isn't. **Always pre-fetch the diff in the parent and embed it inline in the agent prompt** (under a clearly delimited `DIFF:` heading). Verify by re-running `git diff master...HEAD --stat -- <path>` yourself for any "OK" finding on a file you suspected had changes — if `--stat` shows non-zero LOC, the agent failed and you must re-dispatch with the diff embedded.

### Don't trust intermediate output while the script iterates

The Sonnet subagent may rewrite and re-run the script several times. Do not read `.agents/review-triage-summary.txt` for final counts until the agent reports completion — intermediate runs (especially before bugs like the snapshot-extension issue are caught) can produce drastically wrong bucket distributions.
