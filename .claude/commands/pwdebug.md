Attach Playwright via CDP to an existing Chrome (TestCafe t.debug(), Playwright, or any Chrome with --remote-debugging-port) and run JS against the active page.

Invokes the `pwdebug-cdp` skill. Pass inline JS or a .mjs file path as argument:

- `/pwdebug` — show available pages
- `/pwdebug console.log(await page.title())`
- `/pwdebug path/to/script.mjs`
- `/pwdebug page.evaluate(() => document.querySelectorAll("[aria-current]").length)`
