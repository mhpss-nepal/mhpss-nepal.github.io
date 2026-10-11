# Browser regression tests

From a clean checkout with Node.js/npm installed:

```sh
npm ci
npx playwright install chromium
npm run test:skill-loop
npm run test:ui
```

Playwright is pinned in package-lock.json. `PLAYWRIGHT_MODULE` optionally selects an installed Playwright package; otherwise the helper uses `require('playwright')`, with the existing development-server installation only as a last fallback. `CHROMIUM_EXECUTABLE` or `CHROMIUM_PATH` selects a browser; otherwise Playwright's detected executable is used, with the existing development Chromium 1243 as a last fallback.

The tracked Skill Loop fixture is synthetic interface content and its eight images are explicit test dependencies. No private author inputs or audit files are required. The actual-content suite tests the public pinned rendition. A prototype reference screenshot is captured only if the private reference file exists; all core assertions always run. Evidence is written outside this checkout, to `../integration-evidence` and `../correction`; `UI_EVIDENCE_DIR` can relocate the viewport evidence.
