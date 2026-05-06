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

Write `.agents/self-review-list.md`: markdown checklist of every file with score ≥ 7 (high-priority human review tier — DEEP+top REVIEW), sorted by score descending. Each line:

```
- [ ] `<path>` _(score N)_
```

Add a header noting total count and the score threshold used. The threshold can be adjusted up or down based on histogram density — the goal is a list the user can realistically self-review in a few hours.

### Step 6 — Generate self-review guide (rich human-oriented tour)

Write `.agents/self-review-guide.md` — a richer companion to the flat checklist. Generated **before Phase 2 dispatch** so the user can manually review high-risk files in parallel while agents run in background. Overwrite each fresh skill run.

**Generation can be delegated to a Sonnet subagent.** Pass it: `.agents/review-metadata.json`, the pre-fetched diffs in `/tmp/diffs/`, the dimensions from Step 2, and the manual-test rule table below.

#### Three sections

**Section 1 — Common bug patterns (generic, derived from dimensions)**

For each A/B/C/D dimension that has ≥1 hit on the branch, emit a block. Format:

```md
### <Pattern name> (<dimension flag>)
- **Symptom**: <what the user sees if the bug is present>
- **Where**: <path patterns / file types>
- **Verify**: <DOM-inspector hint / side-by-side compare / error-path trigger>
```

Concrete example (when A4 + Pane wrapping has hits):

```md
### Ellipsis broken (A4 + Pane wrapping)
- **Symptom**: text clips without `…`. Looks like cut text mid-word.
- **Where**: any column with fixed width + long content (state labels, user names)
- **Verify**: DOM inspector — `text-overflow: ellipsis` should be on the `<p>`, NOT on the wrapping `<div>`
```

**Section 2 — Per-file annotated (score ≥ 7, sorted desc)**

For each file in the threshold:

- Triage line: `**Triage**: A=N, B=N, C=N, D=N — flags`
- Auto-detected diff patterns (ast-grep + regex against the file's diff): structural Pane wraps with line refs, ellipsis triplet movement, color attr token swaps, testid removals, void prefix locations, className spacing changes (with majorScale→Tailwind equivalence check: `majorScale(N) = N*8px = m_-{2N}`), scope-creep markers
- Self-review checklist: `- [ ] ...` items derived from the patterns
- Manual-test verdict block

Manual-test verdict — derived from this rule table:

| Pattern | Verdict |
|---|---|
| A4 structural in C ≥ 4 | 🔍 REQUIRED |
| A4 in C 1-3 | 🔍 quick check |
| A3 color migration | ⚠️ DESIGNER |
| A2 className in C ≥ 4 | 🔍 spot-check (pixel-equivalence) |
| A2 in non-critical | ✅ skip (typecheck covers) |
| A0/A1 mechanical only | ✅ skip |
| D2 void prefix in money path | 🔍 REQUIRED (verify error path triggers UI) |
| D4 no Paragraph touch | ✅ skip (scope creep, but no direct UI impact) |
| Test/story file | ✅ skip |

When the verdict is 🔍, the block must include a "What to look for" sub-section:

- ✅ **OK behavior**: <what should render correctly>
- 🐛 **Bug behavior**: <symptom of regression>
- **Edge cases**: zero-state, max content, hover states, etc.
- **DOM tell**: what to inspect in devtools to confirm

**Section 3 — Cross-file clusters (auto-detected)**

Group files where ≥3 share the same path-prefix AND the same flag set (e.g. all `pages/draws/DrawPaymentPage/*` with `A=4 + D2-void-prefix`). Format:

```md
## Cluster: <path-prefix> (<count> files, score N-M)

All N files share <flag-signature>.

**Risk concentration**: <why a shared bug pattern affects all of them at once>
**Verification path**: pick 1 representative for deep verification, spot-check the rest.
```

**Color migration extra warning** — A3 changes always need designer review, never auto-approved. Specifically: hex → token mappings can lose semantic intent. `theme.colors.blue900` (dark navy emphasis) → `"secondary"` (muted gray) is a known confusion case. Flag every A3 with ⚠️ DESIGNER.

### Step 7 — Phase 2: dispatch review agents

For each bucket, spawn agents in **background** (`run_in_background: true`):

| Bucket | Agent strategy |
|---|---|
| SKIP | none |
| SCAN | 1 `general-purpose` agent, full bucket as input, prompt: "glance at each file's diff, report only surprises in <2 lines per file" |
| REVIEW | N `pr-review-toolkit:code-reviewer` agents, 3-5 files per agent, prompt: focused review against the dimensions from Step 2 |
| DEEP | 1 `pr-review-toolkit:code-reviewer` agent per file, prompt: detailed review with the file's specific red flags from the triage script |

Each agent is told to return findings in a structured format (file:line / severity / message). Pass the relevant `git diff master...HEAD -- <file>` inline in the prompt — do not let the agent re-fetch it (see Troubleshooting: "Phase 2 agents — pre-fetch diff inline").

For follow-up "fix" agents triggered by Phase 2 findings, the prompt MUST end with: *"After your edit succeeds, stage your changes (`git add <files>`) and create a commit (`git commit -m '<scope>: <one-line summary>'`). Do NOT push."* See Notes: "Sub-agents auto-commit, never push".

### Step 8 — Consolidate findings

When all background agents finish, merge their outputs into `.agents/review-report.md`:

- Group by file path
- Sort by max severity within file, then by score from triage
- Each finding: `**file:line** — severity — message`

### Step 9 — Final summary in chat

Print a compact summary:

```
📊 Triage complete (<total> files)
   DEEP=<n> · REVIEW=<n> · SCAN=<n> · SKIP=<n>

🚨 Scope creep: <n> files in DEEP don't touch <TARGET> — see review-buckets-deep.txt
✅ Self-review checklist: .agents/self-review-list.md (<n> files, threshold score ≥ 7)
✍️  Self-review guide: .agents/self-review-guide.md (<n> files annotated, <n> 🔍 manual tests required)
🤖 Phase 2 review: .agents/review-report.md (<n> findings across <n> files)
```

Omit the scope-creep line if Step 4 was skipped or returned zero hits.

## Notes

- **Always pause before Step 3.** The user explicitly wants to approve dimensions and weights before any code is generated. Never skip Step 2's loop.
- **Buckets go in `.agents/`** (project-local, can be committed if useful, gitignored otherwise). Script goes in `/tmp/` (one-shot, not reusable across branches because dimensions differ).
- **Phase 2 runs in background.** Continue conversation while agents work; results come in via completion notifications.
- **Sub-agents auto-commit, never push.** Every fix or follow-up agent prompt MUST instruct the agent to stage its changes (`git add <files>`) and commit with a `<scope>: <one-line summary>` message after the edit succeeds. **Never push** — pushing requires explicit per-action user approval (per CLAUDE.md "Sistemas externos — autorización explícita"). This gives the user intermediate diff/revert checkpoints without external-system side effects. Recommended commit-message scopes: `fix(<area>):`, `chore(triage):`, `feat(<area>):`.

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

### Sub-agents may have Edit/Bash silently denied for paths outside the worktree

When delegating fixes to sub-agents, occasionally Edit and Bash are blocked even though the agent definition says they're available — typically for paths outside the parent's working directory (e.g. `~/.agents/`, `~/.zsh/`, `~/scripts/`). Symptoms: the agent reports "Edit/Bash denied" or returns instructions for the user to apply manually instead of doing the work.

**Workaround:**
- Use `subagent_type: general-purpose` (it has `Tools: *`)
- Do NOT pass `isolation: "worktree"`
- In the prompt explicitly tell the agent: "Use Read, Edit, Bash directly — these tools are available in your context"
- For yadm-tracked files at `~/.agents/skills/<name>/SKILL.md`: delegation often fails. Fall back to applying the edit in the main parent context, then commit/push via yadm yourself.

If an agent fails on Bash for a yadm command in particular, do not retry — just do it inline.

### Don't trust intermediate output while the script iterates

The Sonnet subagent may rewrite and re-run the script several times. Do not read `.agents/review-triage-summary.txt` for final counts until the agent reports completion — intermediate runs (especially before bugs like the snapshot-extension issue are caught) can produce drastically wrong bucket distributions.
