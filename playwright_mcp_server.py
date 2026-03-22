#!/usr/bin/env python3
"""Python-based Playwright MCP server.

Exposes three browser tools via the MCP stdio protocol:
  - browser_navigate     navigate to a URL
  - browser_take_screenshot  capture the current page as a PNG image
  - browser_wait_for     sleep for N seconds (lets pages finish loading)

Run as a subprocess:
    python playwright_mcp_server.py

The server manages a single Playwright Chromium browser for the lifetime of
the process. There is no persistent state between server restarts.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP, Image
from playwright.async_api import async_playwright, Browser, Page

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Module-level page reference — shared between tool handlers.
# Set once in lifespan, used by all tool calls.
_page: Page | None = None


_STEALTH_SCRIPT = """
// Remove the webdriver flag that every bot-detection script checks first
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Add a minimal window.chrome object — absent in headless, present in real Chrome
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };

// Fake a few plugins so navigator.plugins.length > 0
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [{ name: 'PDF Viewer' }, { name: 'Chrome PDF Viewer' }];
        arr.item = (i) => arr[i];
        arr.namedItem = (n) => arr.find(p => p.name === n) || null;
        Object.setPrototypeOf(arr, PluginArray.prototype);
        return arr;
    },
});

// Realistic language list for an Australian user
Object.defineProperty(navigator, 'languages', { get: () => ['en-AU', 'en-GB', 'en'] });
"""


@asynccontextmanager
async def _browser_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Start Chromium on server startup and close it on shutdown."""
    global _page
    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                # Removes the `AutomationControlled` feature flag that sites
                # check via `navigator.userAgentData` and related APIs.
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            # Windows Chrome UA — Linux UA is suspicious for a real user.
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-AU",
            timezone_id="Australia/Melbourne",
            extra_http_headers={"Accept-Language": "en-AU,en;q=0.9"},
        )
        # Inject stealth patches into every page before any JS runs.
        await context.add_init_script(_STEALTH_SCRIPT)
        _page = await context.new_page()
        logger.info("Playwright browser started")
        try:
            yield
        finally:
            await context.close()
            await browser.close()
            _page = None
            logger.info("Playwright browser stopped")


mcp = FastMCP("playwright-browser", lifespan=_browser_lifespan)


@mcp.tool(description="Navigate the browser to a URL")
async def browser_navigate(url: str) -> str:
    """Navigate to a URL and return the page title.

    Args:
        url: The URL to navigate to.

    Returns:
        A text summary including the final URL and page title.
    """
    page = _page
    if page is None:
        raise RuntimeError("Browser not initialised")
    response = await page.goto(url, wait_until="load", timeout=30_000)
    title = await page.title()
    status = response.status if response else "unknown"
    return f"Navigated to {page.url}\nStatus: {status}\nTitle: {title}"


@mcp.tool(description="Take a screenshot of the current browser page")
async def browser_take_screenshot() -> Image:
    """Capture the visible viewport as a PNG screenshot.

    Returns:
        An Image object containing the PNG screenshot data.
    """
    page = _page
    if page is None:
        raise RuntimeError("Browser not initialised")
    screenshot_bytes: bytes = await page.screenshot(full_page=False, type="png")
    return Image(data=screenshot_bytes, format="png")


@mcp.tool(description="Get the visible text content of the current page (up to 15000 chars)")
async def browser_get_text() -> str:
    """Return the rendered text content of the current page body.

    Calls document.body.innerText which includes text from dynamically
    loaded React/JS content. Truncated to 15000 characters to fit LLM context.

    Returns:
        Visible text content of the page body.
    """
    page = _page
    if page is None:
        raise RuntimeError("Browser not initialised")
    text: str = await page.evaluate("document.body.innerText")
    return text[:15_000]


@mcp.tool(description="Get individual property listing URLs from the current domain.com.au page")
async def browser_get_links(prefix: str = "") -> str:
    """Return individual property listing URLs from the current domain.com.au page.

    Listing URLs follow the pattern:
        https://www.domain.com.au/{address-slug}-{numeric-id}
    e.g. https://www.domain.com.au/1103-4-francis-road-artarmon-nsw-2064-18033311

    The address is embedded in the URL slug (everything before the last -DIGITS).
    Match each URL to a listing by normalising the listing address:
    lowercase, replace '/' with '-', remove commas, replace spaces with '-'.

    Returns:
        Newline-separated list of listing URLs (up to 100).
    """
    page = _page
    if page is None:
        raise RuntimeError("Browser not initialised")
    links: list[str] = await page.evaluate("""() => {
        const seen = new Set();
        const results = [];
        const listingPattern = /^https:\\/\\/www\\.domain\\.com\\.au\\/[^/]+-\\d+\\/?$/;
        for (const a of document.querySelectorAll('a[href]')) {
            const href = a.href.split('?')[0].split('#')[0];
            if (!seen.has(href) && listingPattern.test(href)) {
                seen.add(href);
                results.push(href);
            }
            if (results.length >= 100) break;
        }
        return results;
    }""")
    if not links:
        return "No listing links found."
    # Return each URL with its normalised address slug (strip trailing numeric ID)
    # Format: <normalised-slug> :: <full-url>
    # Agent should normalise the listing address the same way and do an exact startswith match.
    import re as _re
    lines = []
    for url in links:
        path = url.rstrip("/").split("/")[-1]          # e.g. 1103-4-francis-road-artarmon-nsw-2064-18033311
        slug = _re.sub(r"-\d+$", "", path)             # strip trailing -ID → 1103-4-francis-road-artarmon-nsw-2064
        lines.append(f"{slug} :: {url}")
    return "\n".join(lines)


@mcp.tool(description="Wait for the specified number of seconds")
async def browser_wait_for(time: float = 2.0) -> str:
    """Sleep for the given number of seconds.

    Useful after navigation to allow JavaScript and dynamic content to render
    before taking a screenshot.

    Args:
        time: Number of seconds to wait (default: 2.0).

    Returns:
        A confirmation string.
    """
    await asyncio.sleep(time)
    return f"Waited {time:.1f} seconds"


if __name__ == "__main__":
    mcp.run(transport="stdio")
