---
name: upload-pr-screenshots
description: Use whenever local image files (screenshots, captures, evidence, before/after pairs, diagrams) need to land on a GitHub PR — whether to embed in the PR description, post in a comment, or build an Evidence section. Trigger on requests like "upload screenshots to the PR", "attach these images", "embed captures in the PR body", "subir/adjuntar capturas al PR", "ve subiendo las capturas", or any flow that ends with `<img>` tags pointing at github.com/user-attachments URLs. **Never reach for `gh pr edit` with local file paths first** — gh CLI cannot upload binary attachments; this skill is the only working path. Also use when planning a PR description that will reference screenshots, before composing the body, so the URLs exist at edit time.
---

## Task

Upload one or more local image files to a GitHub PR's hosted asset storage and return the `https://github.com/user-attachments/assets/<id>` URLs ready to embed in the PR body.

The technique exploits two facts:
- GitHub's hidden `<input type="file">` accepts `mcp__chrome-devtools__upload_file`.
- React commits the URL to the comment textarea only on synthesized `drop` events, not on `change`.

## Inputs

- PR URL or number.
- One or more absolute paths to local image files.

> **Screenshot path convention:** always save captures to `docs/tickets/<TICKET>/screenshots/` (not `/tmp`). Read `docs/tickets/CURRENT.md` to get the ticket ID if not already known. The directory already exists for active tickets; create it if missing. `/tmp` files are lost between sessions.

## Steps

### Step 1 — Open the PR conversation page

```
mcp__chrome-devtools__new_page url=https://github.com/<org>/<repo>/pull/<n>
```

Wait for the page to load.

### Step 2 — Expose the comment form's hidden file input

```js
() => {
  const input = document.querySelector('form#new_comment_form input[type="file"]');
  input.id = 'cc-mcp-file-input';
  input.style.cssText = 'position:fixed!important;top:200px!important;width:200px!important;height:40px!important;opacity:1!important;z-index:99999!important;visibility:visible!important;';
  return 'tagged';
}
```

Re-take the snapshot — a `Choose Files` button with a fresh `uid` now appears under the comment form. Use that `uid` for `upload_file` in Step 3.

### Step 3 — Per file: upload, drop, capture, clear

```
mcp__chrome-devtools__upload_file uid=<choose-files-uid> filePath=<absolute-path>
```

Then synthesize the drop and poll for the resolved URL:

```js
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const input = document.getElementById('cc-mcp-file-input');
  const ta = document.querySelector('form#new_comment_form textarea[name="comment[body]"]');
  const dt = new DataTransfer();
  dt.items.add(input.files[0]);
  ['dragenter', 'dragover', 'drop'].forEach(t =>
    ta.dispatchEvent(new DragEvent(t, { bubbles: true, cancelable: true, dataTransfer: dt }))
  );
  for (let i = 0; i < 60; i++) {
    if (/user-attachments|user-images|githubusercontent/.test(ta.value)) return ta.value;
    await sleep(500);
  }
  return { value: ta.value, timeout: true };
}
```

Capture the returned `<img …/>` snippet. Then clear the textarea using the React-aware native setter (direct `ta.value = ''` is reverted on next render):

```js
() => {
  const ta = document.querySelector('form#new_comment_form textarea[name="comment[body]"]');
  Object.getOwnPropertyDescriptor(Object.getPrototypeOf(ta), 'value').set.call(ta, '');
  ta.dispatchEvent(new Event('input', { bubbles: true }));
}
```

Repeat for each file.

### Step 4 — Return the URLs

Output the captured `<img …/>` snippets to the caller. **Do not** click the "Comment" button — the textarea is just a scratchpad to extract URLs.

### Step 5 — Embed in the PR body

Compose the Evidence section and run `gh pr edit <n> --body …`:

- **≤ 4 screenshots**: embed each inline with a short label.
- **≥ 5 screenshots**: wrap the entire grid in a single `<details><summary>Show N screenshots</summary>…</details>` (the section heading stays outside).

#### When to pair vs. when to use a single image

**Only pair two images when the comparison is apples-to-apples — i.e. the two screenshots differ in exactly the variable the reviewer is evaluating** (e.g. fix vs. no-fix at the same commit/component, FF on vs. off in the same view). If the second image varies in any other dimension (different component, different commit base, different state) on top of the variable being demonstrated, the pair is misleading and the "after" muddles the claim.

**A single image is the right answer when:**
- The claim is purely existential: "this state existed at commit X" (one capture is the proof).
- The "after" image would be identical to one already shown elsewhere in the body — duplicating it adds noise without information.
- The two captures differ in more than one variable (e.g. comparing legacy component pre-fix to refreshed component post-fix mixes "fix applied" with "component changed").

When in doubt, ask: "what does the right-hand image prove that the left-hand image doesn't already prove on its own?" If the answer is "nothing" or "it duplicates evidence shown elsewhere", drop the pair and use a single image with a clear caption.

#### Side-by-side comparisons (before/after, master/branch, FF off/on)

When two screenshots are genuinely paired (apples-to-apples visual diff per the rule above), use an HTML `<table>` so the images render next to each other instead of stacked vertically. GitHub renders raw HTML inside markdown bodies, so this works without escapes. Always use this pattern for valid pairs — never stack paired captures top-to-bottom; reviewers shouldn't have to scroll between them.

```html
<table>
<tr><th>master</th><th>this branch</th></tr>
<tr>
<td><img width="..." height="..." alt="<view> — master" src="https://github.com/user-attachments/assets/<id-master>" /></td>
<td><img width="..." height="..." alt="<view> — this branch" src="https://github.com/user-attachments/assets/<id-branch>" /></td>
</tr>
</table>
```

Rules:
- Header row labels are required and short — `master` / `this branch`, `before` / `after`, `FF off` / `FF on`. The labels make the diff scannable; reviewers don't have to read alt text.
- One short prose line above each table summarising the difference (or stating "render unchanged" when the table is sanity-check evidence with no expected diff).
- Apply the same format consistently across **every** paired set in one PR. If the main Before/After is in a side-by-side table, every adjacent-panel "no regression" comparison must also use the table — do not mix stacked and side-by-side in the same PR body.
- For trios (e.g. before / annotated / after) keep the single-row table and add a third `<th>`/`<td>` pair.

## Rules

- One file at a time. Multi-file `DataTransfer` works in real DnD but the polling logic above expects a single resolved URL per round.
- If `timeout: true`, read the textarea — GitHub usually wrote `![…](upload error)`. Retry once before giving up.
- The skill never edits the PR body; the caller composes the final body and runs `gh pr edit`.

## Troubleshooting

_Empty — fill in as real failures appear._
