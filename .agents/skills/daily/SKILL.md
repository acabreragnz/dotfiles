---
name: daily
description: Use when the user asks to generate a daily standup update, says "armame la daily", "generate daily", or "standup update".
argument-hint: 'optional focus or override'
---

## Task

Generate a spoken-style daily standup update in English (Done / Doing / Blocked) based on the user's real activity in git, GitHub, and Linear. Show a tight findings summary first, iterate once with the user, then produce the final draft.

If `$ARGUMENTS` is provided, treat it as a focus or scope override (e.g. "only ENG-4670", "include last 3 days").

## Hard rules

- **No invention.** Never mention feedback, reviews, motivations, or blockers that aren't in commits, PRs, or Linear activity. If unsure, ask.
- **English always**, regardless of how the user writes to you.
- **Output only in chat** — do not save files.
- **First person, contractions OK** ("I shipped", "I'm picking up", "it's blocked on"). Speak to the team, not to a manager.
- **Bundle, don't enumerate.** Multiple commits on the same ticket on the same day collapse into one outcome line. Never list commit messages back to the user.

## Step 1 — Resolve the time window

- `today` = current date (use `date '+%A %Y-%m-%d'`).
- `yesterday` = previous working day:
  - If today is Monday → yesterday = last Friday.
  - Otherwise → yesterday = calendar yesterday.
- If `$ARGUMENTS` overrides the window (e.g. "last 3 days"), honor it.

## Step 2 — Collect evidence (parallel, single message)

- **Git**: `git log --since="<yesterday> 00:00" --until="<today> 23:59" --author="<git user.name>" --all --pretty=format:"%h %ai %s"`
- **GitHub PRs**: `gh pr list --author "@me" --state all --limit 30 --json number,title,state,createdAt,updatedAt,url,baseRefName,headRefName,reviewDecision,isDraft` then filter to PRs with activity in the window.
- **PR descriptions (always read for active PRs in the window)**: `gh pr view <n> --json title,body`. The PR body is much richer than commit messages and often contains:
  - **"How it worked before / How it works now"** — clean before/after framing the listener can grasp.
  - **Empty / "to be filled in" sections** for testing, risk, evidence — these change "what I'm doing today" (e.g. "polishing" → "polishing and filling in the evidence sections I left empty").
  - **Long rationale paragraphs** that name the *real* root cause behind a one-liner commit (e.g. a known upstream library bug, an undocumented framework behavior). Surface these as "what ate time" if the commit understated the work.
  - **Diagrams and code-flow trees** showing how a single fix covers multiple UI surfaces — useful framing for "small change, broad scope".
  - **"Stacked on X. Rebase after Y merges."** — explicit dependency notes the user wrote down for themselves.
  Always cross-check the commit message against the PR body before drafting; the commit is the headline, the PR body is the article.
- **Linear**: list issues where the user had movement in the window (assignee=me, updatedAt=-P2D). Note status, project, related branch.
- **`docs/tickets/CURRENT.md` (always read if present)**: this is the user's working notes — Risks (R1, R2, …), Manual testing items (T1, T2, …), Decisions (especially "DEFERRED" / "out of scope"), and Handoff. It's the primary source for *what was hard*, *what's risky*, and *what's deferred*. Use it to enrich the daily — don't just summarize commits.
- **Memex (conditional)**: only consult if at least one of these is true — otherwise skip (it's slow and noisy):
  - The git log shows a **`revert` / `Revert opportunistic`** commit, or a "redo" pattern (`Add X` followed shortly by `Remove X` then `Add X again`).
  - **CURRENT.md has a Risk that mentions "Surfaced in QA" or "originally scoped"** — implies the section was rewritten, the original journey is hidden.
  - The branch was rebased/squashed (commit count in `git log` is much lower than commit count in PR history), so debugging trajectory is lost.
  - The user explicitly references something not in commits.
  
  When triggered, run:
  ```
  memex index --source <project-path>
  memex search "<ticket-id> <key-symptom>" --limit 5
  ```
  Look for: **A/B comparisons** ("X works because Y forwardRefs, mine doesn't"), **abandoned scope** (commits that no longer exist in `git log`), and **decision pivots** ("originally I did X, then reverted to Y"). These are the "what ate time" gold that survives nowhere else.

### For each scope, ask "why am I working on this?"

For every ticket that ends up in the findings, dig into Linear for the **origin / motivation** before drafting. The mechanical "what I did" is in commits; the *why* lives in Linear and gives the standup its narrative spine. Concrete checks:

- **Who created the ticket?** Self-created → strategic / planned work. Created by someone else → reactive (bug report, customer ask, design review).
- **`createdBy` + `attachments`** often link the original Slack thread or screenshot. The first attachment is frequently the **inbound message** ("Found a spot where X doesn't work") — quote the trigger in plain English.
- **`relations` (relatedTo / blockedBy)** + the description's `## Related` / `## Context` sections explain *which previous ticket made this one necessary*. ("Tooltip refresh added 3 Popover callers → Popover refresh becomes natural next step.")
- **`labels`** (Bug, regression, customer-impacted) and **`projectMilestone`** tell you the category — bug-fix vs planned refresh vs incident. Frame accordingly.
- **`startedAt` vs `createdAt`** — long delta means the ticket sat in backlog; short delta means it was picked up urgently.
- **Don't infer status-transition dates.** Linear exposes `startedAt` (first time the ticket entered any "started" state) and `completedAt` — but NOT the transition into specific statuses like "In Review". A ticket can sit in "In Progress" for days before moving to "In Review", and `startedAt` won't reflect that. Same for PRs: `createdAt` ≠ "in review since X" — it just means the PR was opened. If you don't have a verified timestamp for "in review since", say "already open and waiting for review" instead of inventing a date.
- **Check the actual PR draft state before saying "before asking for review" or "still polishing locally".** Use `gh pr view <n> --json isDraft,reviewDecision`. If `isDraft: false`, the PR is *already* asking for review — even if `reviewDecision` is empty (no one has reviewed yet). Frame today's polish as "on top of the published PR", not "before asking for review". Conversely, only say "still in draft" / "before publishing" if `isDraft: true`.
- **Customer impact**: if the description mentions specific customers ("Stream Realty", "customer X reported"), surface that — it changes the standup priority story.

When the bug fix is a regression in *your own previous work*, say so explicitly. ("Regression in my own Radio refresh that Kelly reported in Slack" beats "fixed a radio bug".) That signals ownership without burying it.

Format the "why" as a short clause in a dedicated column of the findings table, OR as a parenthetical after the ticket name if there's only one ticket. Don't pad — one clause per ticket, max 15 words.

### Don't assume "commit prefix = active ticket"

A commit `[ENG-XXXX]` does NOT mean the user was *working on* ENG-XXXX that day. Common case: the user is on driver ticket **A**, hits an issue that lives in the API of dependency ticket **B** (already published / in review), and pushes the fix to **B's PR** because that's where the code lives. The commit prefix is **B**, but the work was driven by **A**.

To detect this:

- **Check the dependency ticket's Linear status & PR draft state at the start of the window.** If status was already `In Review` / `Done` and the PR was non-draft *before* the commits in question landed, those commits are almost certainly surfaced side work, not resumed development.
- **Cross-reference with the driver ticket's preflight / risks.** If CURRENT.md for driver A lists a verification item (T3: "typeahead via `textValue`") and dependency B's commit on the same day is "Add textValue …", that's the smoking gun: it's A's preflight finding, patched into B's PR.
- **Stacked PR + same-day commits on parent** = strong signal of "preflight-driven patch", not "two parallel streams".

When this pattern fires, frame it explicitly in the findings: "while preflighting A, surfaced two fixes that had to land in the still-open B PR" — not "worked on A and B".

### Effort signals to extract

Read commits + CURRENT.md for these signals — they tell you which work was non-trivial vs routine. Surface 0–2 in the findings (don't dump all):

- **Repeated commits on the same narrow surface** (e.g. 4 commits on "hover popover gap" today) → that surface ate time.
- **Commit verbs**: `fix`, `revert`, `restore`, `match X to Y`, `replicate master`, `stop X from`, `address feedback` → corrective work, not greenfield.
- **CURRENT.md Risks (`### R<n>`) marked with explicit verification or "surfaced in QA"** → real gotchas, not theoretical.
- **CURRENT.md "DEFERRED" / "out of scope" / "follow-up"** → scope decisions worth mentioning if recent.
- **A revert immediately followed by a different-shape reimplementation** → the first approach didn't work; the user learned something.
- **Cross-ticket compat bridges or workarounds** (e.g. "extend Menu compat bridge to cover refreshed Popover") → integration cost, often the time sink.

When surfacing one in the draft, name the *symptom* and the *fix in plain English*, not the commit subject. Example: "the hover popover lost its visual gap after the refresh — matched master's inline-text + Pane marginTop to bring it back" beats "replicate master's inline-text + Pane marginTop for hover popover gap".

## Step 3 — Detect relationships before listing

Apply these heuristics so unrelated-looking work groups correctly:

- **Stacked PRs**: PR `baseRefName` ≠ `master`/`main` → stacked. Find the parent and state the dependency as a fact (don't ask).
- **Interleaved commits**: commits on multiple tickets within the same hour/worktree → likely surfaced while doing the main work.
- **Cross-ticket commit messages**: a commit on ticket A that mentions ticket B → A is the driver, B is the side effect.

When any heuristic fires, group as **driver + surfaced side work**, not as separate streams.

**Bundling rule:** for any (ticket, day) pair with ≥2 commits, write ONE outcome line that names the deliverable. Examples:
- 8 polish commits on ENG-4670 → "polish pass on the hover popover"
- 5 wrapper + caller commits → "wired the new Popover wrapper and migrated the hover callers"
- Never write "fixed X, then fixed Y, then fixed Z, then …".

## Step 4 — Show findings (structured, emoji-rich, table-driven)

**Format rule: tables and emoji-prefixed sections, never flat bullet lists.** The user wants findings to read as a scannable dashboard, not a meeting transcript. Group by status into separate H3 sections; each section is a table (or a 2-column emoji-led table when there's only 1–2 items). One line per ticket per day, max. Keep outcome / plan cells under ~12 words.

Use this exact shape — emit only the sections that have content:

```
## 📋 Findings — <day> <date> → <day> <date>

### 🚀 Shipped / Merged
| Ticket | PR | Status | Highlight |
|---|---|---|---|
| 🐛 ENG-XXXX <short name> | [#NNNN](url) | ✅ Merged today | <one-line outcome> |

### 🔄 In Review
| Ticket | PR | What happened in window |
|---|---|---|
| 🪟 ENG-XXXX <short name> | [#NNNN](url) | 📤 Published yesterday + N polish commits today |

### 🏗️ <Driver ticket> — work breakdown
(Only when one ticket dominates the window with ≥4 commits across distinct surfaces. Skip otherwise.)

| When | What |
|---|---|
| 🕓 Yesterday afternoon | <plain-English deliverable> 🧱 |
| 🕘 Late yesterday | <plain-English deliverable> 🌉 |
| 🕛 Today | <plain-English deliverable> |

### 🛠️ Started
| Ticket | PR | Status |
|---|---|---|
| ⌨️ ENG-XXXX <short name> | [#NNNN](url) | 📝 Draft, In Progress |

### ⏳ PRs sitting in review (potential blockers?)
| PR | Ticket | Open since |
|---|---|---|
| #NNNN | 🪟 <short name> | <date> |

### 🧨 What ate time / gnarly bits
|     | Symptom → fix |
|---|---|
| 🔬 | <plain-English symptom + fix> |
| 🪝 | <integration cost> |

(0–2 rows max. Skip the section entirely if the day was routine — don't manufacture drama.)

### 🚧 Blockers (facts, not questions)
|     | Blocker |
|---|---|
| ⛓️ | #NNNN is stacked on #MMMM — #MMMM not merged |
| 🛑 | #PPPP has CHANGES_REQUESTED |

### ❓ Before I draft
1. Anything to filter out, correct, or add?
2. Are any of those open PRs actually **blocking** you, or just waiting on review?
```

**Hard formatting rules for findings:**
- Every ticket row leads with a topical emoji (🪟 popover, 📜 menu, ⌨️ input, 🔘 button, 🎚️ switch, 🐛 bug, etc.) — pick one that hints at the surface.
- Status emoji uses the legend below.
- PR links are markdown links to the GitHub URL, not bare `#NNNN` (so the user can click).
- Never emit a flat top-level bullet list (`- foo`) for findings. If a section has only 1–2 items, still use a 2-column emoji-led table.
- Bundle commits per (ticket, day): one outcome row, never one row per commit.

**Status / topic emoji legend:**
- 🆕 new ticket started in the window
- 🔁 continuing a ticket from before
- ↪️ surfaced/side work from a driver ticket
- 🐛 bug fix
- ✅ merged / deployed in the window
- 📤 PR published (out of draft)
- 📝 PR still draft
- ⏳ waiting on review (not blocking unless user says so)
- ⛓️ stacked dependency
- 🛑 changes requested
- 🚫 explicit Linear "Blocked" status
- 🔬 gnarly bit — risk that became real, debugging that took non-trivial time, or a corrective revert+redo
- 🪝 integration cost — compat bridge, stacked-PR coordination, scope decision (e.g. deferred caller migration)

After emitting the findings tables, ask **one** question (the "Before I draft" block above already does this). Wait for the user.

## Step 5 — Draft the update

Style contract:
- **Length: 150–200 words total.** Aim for ~1 minute spoken. Cut anything that doesn't move the standup forward, but don't strip the *specifics* (which preflight fix, which caller, who reported the bug) — those are what make it informative vs. generic.
- **Shape: 2–4 short paragraphs**, whichever fits. Done / Doing / Blocked is the typical structure but split when one bucket is heavy. One ticket → one paragraph is fine. Don't pad.
- **Done (past tense)** — name the deliverable, not the activity. "Shipped the Popover refresh PR, stacked on Menu" beats "worked on popover stuff".
- **Doing (present continuous)** — the specific next thing. "Today I'm polishing the hover popover gap and then picking up TextInput."
- **Blocked** — concrete blocker + who/what unblocks it, or "no blockers". Never invent one. Stacked PRs count as blockers only if review is the bottleneck — say so plainly.
- **Surface at most one "gnarly bit"** if the day had one — name the symptom, the fix in plain English, and stop. ("Hit a focus-stealing bug on the hover popover, fixed by disabling auto-focus.") Don't surface routine work this way.
- **Skip**: every-commit detail, "same as yesterday", personal stuff, internal refactor noise the team doesn't care about.
- **Tone**: huddle, not status report. Contractions are good. No corporate filler ("circle back", "touch base").
- **Translate API-level details into behavior the listener can picture.** Standup listeners (PMs, designers, other engineers on different surfaces) don't have your preflight or PR-review context. Prop names, internal component names, and dev shorthand should be replaced by user-visible symptoms.
  - ❌ "typeahead via `textValue` on `Menu.Item`s with JSX children" → ✅ "keyboard typeahead breaking when menu items have icons or other rich content"
  - ❌ "rendered at viewport 0,0" → ✅ "rendered at the top-left corner of the screen"
  - ❌ "I extended the `:has()` bridge selector" → ✅ "I extended the CSS workaround that hides the duplicate borders"
  - Keep technical names that the team genuinely shares (`cloneElement`, `forwardRef`, the PR/issue numbers) — just don't bury the symptom under them. Rule of thumb: if removing the prop name and replacing it with the user-visible behavior loses zero information for the listener, drop the prop name.

## Step 6 — Iterate

Present the draft. Apply user corrections directly. Common corrections:
- PR was actually published, not draft (or vice versa).
- Missing side-work the user did but didn't commit.
- Reframe side task as part of the main ticket.
- More/less detail.
- Tone too formal or too casual.

Keep iterating until the user signals it's good. Never re-ask questions already answered in the same run.

## Troubleshooting

- **Sparse activity (1–2 commits, no PR):** ask the user what else they touched before drafting — don't pad with irrelevant tickets.
- **Multiple active tickets with similar weight:** lead with the one that has movement *today*, not the one with most yesterday-commits.
- **User pushes back on tone repeatedly:** ask for a one-line tone reference ("more like X, less like Y") and apply it; don't keep guessing.
