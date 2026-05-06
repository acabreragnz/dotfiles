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

Write `/tmp/triage-<branch-slug>.py` with everything embedded (no imports from `docs/`). **Delegate this step to a Sonnet subagent** (`Agent` with `subagent_type: general-purpose`, `model: sonnet`) — the script is mechanical and the parent context shouldn't burn tokens on it.

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

`docs/tickets/<TICKET>/review-buckets-{deep,review,scan,skip}.txt` (one path per line), `docs/tickets/<TICKET>/review-triage-summary.txt` (counts + score histogram + top-30 table), and `docs/tickets/<TICKET>/review-metadata.json` (per-file score, dims, flags, plus `diff_path` pointing into the worktree-local `_diffs/` dir). Run from repo root: `python3 /tmp/triage-<branch-slug>.py`.

**Pre-fetched diffs** must land in `docs/tickets/<TICKET>/_diffs/<sanitized>.diff` (one per file) — **never** `/tmp/diffs/`. Subagents can't read `/tmp/` (sandbox isolation), and Step 6 batch agents need to Read these files to write the self-review guide. The script must `mkdir -p docs/tickets/<TICKET>/_diffs/` and write each `git diff master...HEAD -- <path>` there. The sanitized filename rule: replace `/` with `_`, **preserve the original extension** (see Troubleshooting note).

**Resolve `<TICKET>`** from `docs/tickets/CURRENT.md` (read the first line — `# ENG-NNNN: ...`). Fallback to the current branch name's `ENG-NNNN` token if CURRENT.md is missing or stale.

### Step 4 — Sanity check for scope creep

If `$ARGUMENTS` named a target component or pattern, audit the DEEP bucket: for each file, check whether its diff actually touches that target. Report files that don't (likely scope creep from another feature). Wait for the user to filter or confirm before Step 5.

If no target was given, skip this step.

### Step 5 — Generate self-review checklist

Write `docs/tickets/<TICKET>/self-review-list.md`: markdown checklist of every file with score ≥ 7 (high-priority human review tier — DEEP+top REVIEW), sorted by score descending. Each line:

```
- [ ] `<path>` _(score N)_
```

Add a header noting total count and the score threshold used. The threshold can be adjusted up or down based on histogram density — the goal is a list the user can realistically self-review in a few hours.

### Step 6 — Generate self-review guide (rich human-oriented tour)

Write `docs/tickets/<TICKET>/self-review-guide.md` — a richer companion to the flat checklist. Generated **before Phase 2 dispatch** so the user can manually review high-risk files in parallel while agents run in background. Overwrite each fresh skill run.

**Generation can be delegated to a Sonnet subagent.** Pass it: `docs/tickets/<TICKET>/review-metadata.json`, the pre-fetched diffs in `docs/tickets/<TICKET>/_diffs/`, the dimensions from Step 2, and the manual-test rule table below.

**🚨 Subagent I/O paths must live inside the worktree, never in `/tmp/`.** Claude Code's sandbox derives subagent allowed-paths from the parent's primary working directory; `/tmp/` is reachable from the parent but **not from subagents**, even with `mode: "bypassPermissions"`. Confirmed by upstream issues #32034, #45888, #29048 — Read/Write/Bash on `/tmp/` paths get silently denied inside subagents. The fix: route all subagent I/O through `docs/tickets/<TICKET>/_diffs/` (inputs) and `docs/tickets/<TICKET>/_scratch/` (outputs). Both are inside `docs/tickets/`, which is in the user's global `~/.gitignore` → local-only, never committed. The Step 3 triage script must write diffs to `docs/tickets/<TICKET>/_diffs/<sanitized>.diff`, not `/tmp/diffs/`.

**Scale rule — batch when score ≥ 7 yields > 12 files.** A single agent generating 30+ annotated file blocks frequently hits the API's ~10 min stream-idle timeout (model accumulates context, re-reads diffs, and stalls mid-generation). Instead:

- Split files into batches of **6-8 each**, group by score-desc so each batch is roughly homogeneous
- Dispatch **N parallel Sonnet agents in background** (one per batch) — each writes its slice to `docs/tickets/<TICKET>/_scratch/guide-batch-<N>.md` (inside the worktree, NOT `/tmp/`)
- The parent context handles **Section 1** (generic patterns from dimensions) and **Section 3** (cross-file clusters from metadata) — these don't need per-file iteration, so do them inline
- Concatenate at the end: `cat <(echo header) docs/tickets/<TICKET>/_scratch/guide-batch-*.md section3 > docs/tickets/<TICKET>/self-review-guide.md`

**Per-batch prompt budget rules** (keeps each agent fast and timeout-resistant):

- Hard cap **30 lines per file block**
- "Don't quote diffs in output — point at line refs only" (e.g. "L34: Pane wraps Paragraph; ellipsis on inner `<p>` ✓")
- Pre-extract metadata fields (path, score, A/B/C/D, flags, diff path) into the prompt as a bullet list — the agent shouldn't re-derive them from JSON
- Tell the agent its scope is exactly N files and the output goes to one file under `docs/tickets/<TICKET>/_scratch/` — no header, no Section 1/3
- **Never** ask a subagent to read or write `/tmp/`. If a diff path looks like `/tmp/diffs/...`, fix the upstream Step 3 script first; don't paper over it in the agent prompt.

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

Each file gets a **narrative block, not a checklist dump**. The reviewer should be able to read it like prose and walk away knowing what could break and where to look. Bullet-soup with mechanical detections (`majorScale(2) → mt-4` ✓) buries the signal.

**Required structure**:

```md
## `<path>` _(score N)_

**Triage**: A=N B=N C=N D=N — flags

**Lo que cambió y por qué importa**

<1-3 sentences framing what's in the diff. Distinguish the "innocent" mechanical
moves (Pane wraps with layout-prop relocations, mapped prop renames, equivalent
className conversions) from the spots that introduce real uncertainty. Name
specific line refs only for the risky parts. If everything is mechanical, say so
in 1 sentence and stop — don't invent things to flag.>

[If there's a meaningful before/after worth seeing, include a small code block:]

```jsx
// Antes
...

// Después
...
```

**Por qué funcionaba antes**: <one short paragraph explaining the prior behavior
and why it worked, even if it was an anti-pattern>.

**Por qué puede no funcionar ahora**: <one short paragraph explaining what changed
in the DOM/CSS/runtime that breaks the prior behavior; what the user-visible
symptom would be>.

**Verificación + fix**: <one paragraph combining (a) what to inspect in DevTools
or rendered output to confirm, (b) the suggested fix, and (c) any bonus side-effect
the fix resolves>.

**Manual test**: <verdict from rule table>
```

**Filtering rules — what NOT to write under "Lo que cambió"**:

- ❌ `pl-2 = 8px = majorScale(1)` ✓ — mechanical equivalence we already trust
- ❌ "Import reorder only (no semantic change)" — non-events
- ❌ `fontWeight={300}` mapped to `weight="regular"` per WEIGHT_MAP — predictable
- ❌ Listing every Pane wrap when most just relocated layout props
- ❌ Self-review checklist of items the reviewer would already check naturally

**What TO write**:

- ✅ Anti-patterns that were *partially* resolved by the migration (e.g. flex chain broken because `<Paragraph>` stayed in the middle)
- ✅ Behavior changes implied by the migration (e.g. `overflow:inherit` → `overflow:visible`, `key={index}` → `key={item.id}`)
- ✅ Conversions where the equivalence is doubtful or arbitrary (e.g. `className="px-[5px]"` arbitrary value, `text-[#0A1433]` raw hex instead of token)
- ✅ Scope creep refactors mixed into the migration commit (reduce → for-of, void prefixes)
- ✅ Color token semantic mismatches worth designer attention

**Length budget**: aim for ~15-25 lines per file block when there's something worth saying. For pure-mechanical files, 3-5 lines is enough ("Todo mecánico — Pane wraps con relocations 1:1, classNames equivalentes. ✅ skip"). Don't pad.

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

When all background agents finish, merge their outputs into `docs/tickets/<TICKET>/review-report.md`:

- Group by file path
- Sort by max severity within file, then by score from triage
- Each finding: `**file:line** — severity — message`

### Step 9 — Final summary in chat

Print a compact summary:

```
📊 Triage complete (<total> files)
   DEEP=<n> · REVIEW=<n> · SCAN=<n> · SKIP=<n>

🚨 Scope creep: <n> files in DEEP don't touch <TARGET> — see review-buckets-deep.txt
✅ Self-review checklist: docs/tickets/<TICKET>/self-review-list.md (<n> files, threshold score ≥ 7)
✍️  Self-review guide: docs/tickets/<TICKET>/self-review-guide.md (<n> files annotated, <n> 🔍 manual tests required)
🤖 Phase 2 review: docs/tickets/<TICKET>/review-report.md (<n> findings across <n> files)
```

Omit the scope-creep line if Step 4 was skipped or returned zero hits.

## Notes

- **Always pause before Step 3.** The user explicitly wants to approve dimensions and weights before any code is generated. Never skip Step 2's loop.
- **All artifacts go in `docs/tickets/<TICKET>/*`** — matches the `ticket` skill convention (one directory per ticket, `<TICKET>.md` is the canonical ticket file, screenshots/progress/plans/triage all live as siblings inside the directory). `docs/tickets/` is in the user's global `~/.gitignore` → these artifacts are LOCAL ONLY, never committed to the PR. Resolve `<TICKET>` from `docs/tickets/CURRENT.md` (it's a symlink to `<TICKET>/<TICKET>.md`; use `readlink docs/tickets/CURRENT.md` and parse the prefix) or branch name fallback (`eng-(\d+)` regex on `git branch --show-current`). Script goes in `/tmp/` (one-shot, not reusable across branches because dimensions differ).
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

### Step 6 self-review-guide — single-agent timeout

A single Sonnet subagent asked to generate the entire self-review guide for **30+ files** will frequently hit the API's `Stream idle timeout - partial response received` error (~10 min idle limit). Symptoms: agent runs for 100+ minutes with dozens of `Read` tool calls (one per diff), accumulates context, and silently stalls mid-generation. The output file may not be written at all, or the file shown is from a previous skill run (wrong timestamp — verify with `ls -la`).

**Fix**: always batch. Per Step 6 "Scale rule — batch when score ≥ 7 yields > 12 files":
- Split into 6-8 file batches → N parallel Sonnet agents → each writes `docs/tickets/<TICKET>/_scratch/guide-batch-<N>.md` (worktree-local, NOT `/tmp/`)
- Parent context handles Section 1 (patterns) and Section 3 (clusters) inline
- Concatenate at the end

A 31-file run that timed out as one agent completed cleanly in <2 min as 4 parallel batches of 8/8/8/7 files. The fan-out also dramatically reduces tail latency vs serial generation.

### Subagent sandbox — `/tmp/` paths silently denied

Subagents (any `subagent_type`, with or without `mode: "bypassPermissions"`) **cannot Read, Write, or Bash on `/tmp/` paths**. The parent session can; subagents cannot. This is a Claude Code sandbox bug, not a misconfiguration.

**Symptoms**:
- Agent reports "Permission to use Read/Write/Bash has been denied" on `/tmp/foo`
- Agent runs for 200+ seconds making 25+ tool calls trying to write a `/tmp/` file
- Agent returns the full output as a string in its `result` (because it couldn't persist) and asks you to grant permission
- `mode: "bypassPermissions"` does NOT help — the sandbox is OS-level (bwrap) and runs below the permission system

**Upstream issues**: anthropic/claude-code #32034 (root cause: sandbox derives allowed paths from primary working dir, doesn't propagate additional dirs to subagents), #45888 (Read/Edit denied on subagent's own worktree even with `isolation: "worktree"` + `bypassPermissions`), #29048 + #52962 (Write/Edit run in-process via `fs.writeFileSync`, sandbox restrictions only apply to Bash via bwrap).

**Workaround for this skill**: route ALL subagent I/O through worktree-local paths inside `docs/tickets/<TICKET>/`:
- Inputs: pre-fetched diffs at `docs/tickets/<TICKET>/_diffs/<sanitized>.diff`
- Outputs: scratch fragments at `docs/tickets/<TICKET>/_scratch/guide-batch-<N>.md`

Both `_diffs/` and `_scratch/` are inside `docs/tickets/`, which the user's global `~/.gitignore` excludes — local-only, never committed. The parent context (Step 3 script, Step 6 concatenation, Step 7 inline-diff embedding) is the only place `/tmp/` is acceptable, and even then prefer the worktree for anything that might cross a subagent boundary later.

**If you find yourself dispatching a subagent and it complains about `/tmp/`**: do NOT redispatch with `bypassPermissions` (won't help). Either (a) rerun with the path moved into the worktree, or (b) salvage the inline `result` content the agent returned and write it from the parent.

### Don't trust intermediate output while the script iterates

The Sonnet subagent may rewrite and re-run the script several times. Do not read `docs/tickets/<TICKET>/review-triage-summary.txt` for final counts until the agent reports completion — intermediate runs (especially before bugs like the snapshot-extension issue are caught) can produce drastically wrong bucket distributions.
