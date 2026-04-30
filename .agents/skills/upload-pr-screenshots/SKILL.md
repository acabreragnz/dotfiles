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

## Rules

- One file at a time. Multi-file `DataTransfer` works in real DnD but the polling logic above expects a single resolved URL per round.
- If `timeout: true`, read the textarea — GitHub usually wrote `![…](upload error)`. Retry once before giving up.
- The skill never edits the PR body; the caller composes the final body and runs `gh pr edit`.

## Troubleshooting

_Empty — fill in as real failures appear._
