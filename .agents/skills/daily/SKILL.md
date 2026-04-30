---
name: daily
description: Use when the user asks to generate a daily standup update, says "armame la daily", "generate daily", or "standup update".
argument-hint: 'optional focus or override'
---

## Task

Generate a spoken-style daily standup update in English (Done / Doing / Blocked) based on the user's real activity in git, GitHub, and Linear. Show findings first, then iterate with the user before producing the final draft.

If `$ARGUMENTS` is provided, treat it as a focus or scope override (e.g. "only ENG-4670", "include last 3 days").

## Hard rules

- **No invention.** Never mention feedback, reviews, motivations, or blockers that aren't in commits, PRs, or Linear activity. If unsure, ask.
- **English always**, regardless of how the user writes to you.
- **Output only in chat** — do not save files.
- **Conversational tone**, not bullet dump. Spoken huddle, not a report.

## Step 1 — Resolve the time window

- `today` = current date.
- `yesterday` = previous working day:
  - If today is Monday → yesterday = last Friday.
  - Otherwise → yesterday = calendar yesterday.
- If `$ARGUMENTS` overrides the window (e.g. "last 3 days"), honor it.

## Step 2 — Collect evidence (parallel)

Run these in parallel via a single message:

- **Git**: `git log --since="<yesterday> 00:00" --until="<today> 23:59" --author="<git user.name>" --all --pretty=format:"%h %ai %s"`
- **GitHub PRs**: `gh pr list --author "@me" --state all --limit 30 --json number,title,state,createdAt,updatedAt,url` then filter to PRs with activity in the window.
- **Linear**: query issues where the user had movement in the window — comments, status changes, assignment changes, branch links — using the linear MCP. Focus on tickets the user is related to (assignee, creator, subscriber, commenter).
- **Memex**: only consult if the above is sparse or the user references something not in commits.

## Step 3 — Show findings first

Present a compact summary of what was found, grouped by ticket / theme. The user must filter or add context before drafting:

```
Found:
- ENG-XXXX (PR #NNNN): <commits summary>
- ENG-YYYY (no PR): <activity>
- Merged: <PR list>
- Side work: <commits not tied to a ticket>

Anything to filter out, add, or correct before I draft?
```

Wait for user feedback.

## Step 4 — Ask about blockers

Detect signals from the evidence:
- PR stacked on a non-merged dependency
- PR with `CHANGES_REQUESTED` review state
- PR awaiting review > 2 days with no movement
- Linear ticket in "Blocked" status

Surface them as questions, not assertions:

```
Possible blockers I noticed:
- PR #NNNN is stacked on #MMMM (not merged yet)
- PR #PPPP has changes requested

Are any of these actual blockers? Anything else blocking you?
```

Default to "no blockers" if the user says nothing applies.

## Step 5 — Draft the update

Apply the spoken-daily best practices:

- **Done (past tense)** — what shipped/merged/finished. Name the deliverable, not the activity. "Published the Popover refresh PR" beats "worked on the popover stuff."
- **Doing (present continuous / future)** — what you're working on today. Name the specific task.
- **Blocked** — specific blocker + who/what is needed, or "No blockers." Never manufacture one.

Style:
- 3 short paragraphs (not bullets), conversational, B2+ English.
- Group by outcome / ticket — don't list every commit.
- Skip the obvious ("same as yesterday"), the personal, and detail that belongs in a follow-up.
- Speak to the team, not to a manager.
- Total length: aim for ~30 seconds spoken.

## Step 6 — Iterate

Present the draft. Apply user corrections directly. Common corrections to expect:
- Wrong assumption (PR was actually published, not draft)
- Missing side-work the user did but didn't commit
- Reframe a side task as part of the main ticket
- Change of detail level

Keep iterating until the user signals it's good.

## Troubleshooting

(empty)
