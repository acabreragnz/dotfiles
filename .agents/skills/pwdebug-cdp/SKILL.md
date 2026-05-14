---
name: pwdebug-cdp
description: Use when attaching Playwright via CDP to an existing Chrome launched with --remote-debugging-port (TestCafe t.debug(), Playwright, or any Chrome debug session) to inspect DOM, evaluate JS, or query the page state interactively.
---

# pwdebug-cdp — Playwright CDP Debugger

Attach to a running Chrome via CDP and execute JS against it. No new browser is launched.

## Task

Write a `.mjs` script in a temp dir, then run it with `~/.asdf/shims/node`.

### Step 1 — Detect CDP port

```bash
ps -ef | grep -oE '\-\-remote-debugging-port=[0-9]+' | grep -oE '[0-9]+' | sort -u
```

- If 0 results → error: "No Chrome with --remote-debugging-port detected."
- If multiple unique ports → list them and ask which to use with `--port N`.
- If exactly 1 → use it.

### Step 2 — Write the .mjs runner

```js
import { chromium } from "/home/tcabrera/dev/rabbet/lift/node_modules/playwright/index.mjs";

const browser = await chromium.connectOverCDP("http://localhost:PORT");
const pages = browser.contexts().flatMap(c => c.pages());
```

Playwright path fallback order:
1. `/home/tcabrera/dev/rabbet/lift/node_modules/playwright/index.mjs` (primary)
2. Run `` `~/.asdf/shims/npm root -g`/playwright/index.mjs `` (global)
3. Error if neither exists

### Step 3 — Select the target page

Filter pages by URL substring (default: `"localhost"`):

```js
const matching = pages.filter(p => p.url().includes("localhost"));
if (matching.length === 0) { /* error + list available pages */ process.exit(1); }
if (matching.length > 1) { /* error: ambiguous, list and ask --url-contains */ process.exit(1); }
const page = matching[0];
const context = page.context();
```

### Step 4 — Append user code and run

Append the user's JS (from $ARGUMENTS — inline or from a .mjs file) after the boilerplate. Then:

```bash
~/.asdf/shims/node /tmp/pwdebug_run.mjs
```

Always use `~/.asdf/shims/node` — never `node` raw or `~/.asdf/installs/nodejs/lts/bin/node` (that path doesn't resolve local node_modules like playwright).

## Common use cases

```js
// List all pages
pages.forEach((p, i) => console.log(`[${i}] ${p.url()}`));

// Page title
console.log(await page.title());

// DOM query
const n = await page.evaluate(() => document.querySelectorAll("[aria-current]").length);
console.log(n);

// Locator
const btn = page.locator("button:has-text('Save')");
console.log(await btn.count());

// Click an element
await page.locator("[aria-label='Close']").click();
```

## Gotchas

- **Do NOT use `Escape` to close popovers** — it also closes slideouts/drawers.
- **Do NOT launch a new Chrome** — `connectOverCDP` attaches to an existing one.
- **TestCafe t.debug()** pauses the test runner and leaves Chrome fully interactive via CDP; page state is intact.
- **Multiple chrome processes** — if there are several, each has its own CDP endpoint. Parse unique ports and prompt the user.
- **Node version matters** — `~/.asdf/shims/node` resolves `.tool-versions` (v24 or whatever is active). The lts alias path (`~/.asdf/installs/nodejs/lts/`) won't see local node_modules; always use the shim.
- **MCP chrome-devtools conflict** — if MCP chrome-devtools is also running, it owns its own tab. Don't close or reuse it; use `connectOverCDP` to attach separately.

## Troubleshooting
