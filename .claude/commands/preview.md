---
name: preview
description: Screenshot the running app with Playwright and review the UI design
argument-hint: [url]
allowed-tools:
  - Bash
  - Read
---

Take a screenshot of the running app using Playwright and review the design.

## When to invoke automatically

Run this skill automatically after every change to `templates/index.html` — no need for the user to ask. Always screenshot and review before considering a frontend task done.

## Steps

1. Check the server is running:
```bash
curl -s http://localhost:8000/health
```
If not running, tell the user to start it with `/dev-server`.

2. Use Playwright to screenshot the page:
```bash
cd /home/mark/hobby && /home/mark/miniconda3/envs/rental-search/bin/python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 900})
        await page.goto('http://localhost:8000')
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path='/tmp/preview.png', full_page=True)
        await browser.close()
        print('Screenshot saved to /tmp/preview.png')

asyncio.run(main())
"
```

3. Read the screenshot:
Use the Read tool to view `/tmp/preview.png` as an image.

4. Review the design and report:
- Overall aesthetic impression
- Typography rendering
- Color contrast and readability
- Layout and spacing
- Any visual issues or misalignments
- Suggestions for improvement if needed
