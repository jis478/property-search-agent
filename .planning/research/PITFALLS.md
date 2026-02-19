# Pitfalls Research

**Domain:** LangGraph ReAct agent + Playwright MCP + FastAPI SSE + LangFuse + domain.com.au scraping
**Researched:** 2026-02-19
**Confidence:** MEDIUM (training data through Aug 2025; Playwright MCP is relatively new; domain.com.au bot detection specifics are MEDIUM confidence)

---

## Critical Pitfalls

### Pitfall 1: MCP Server Process Not Cleaned Up on FastAPI Shutdown

**What goes wrong:** Playwright MCP subprocess left running as zombie on shutdown. Accumulated Chromium processes consume RAM and file descriptors; next startup may fail.

**Why it happens:** `asyncio` subprocesses not automatically awaited on shutdown. Grandchild `chromium` processes are not direct children of FastAPI so aren't OS-killed.

**How to avoid:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp_client = await create_mcp_client()
    try:
        yield
    finally:
        await app.state.mcp_client.aclose()

app = FastAPI(lifespan=lifespan)
```
Run MCP server under a process group so `SIGTERM` kills all Chromium children.

**Warning signs:** `ps aux | grep chromium` growing count; `OSError: Address already in use` on MCP port at startup.

**Phase:** Phase 1 (Foundation) — before any integration work.

---

### Pitfall 2: LangGraph Infinite Agent Loop (Missing Recursion Limit)

**What goes wrong:** ReAct agent loops indefinitely when Playwright returns empty content (bot-blocked page). Default `recursion_limit` is 25 — runs up 25x expected tokens before crashing with unhandled `GraphRecursionError`.

**How to avoid:**
```python
from langgraph.errors import GraphRecursionError

async for event in graph.astream(
    {"messages": [HumanMessage(content=query)]},
    config={"recursion_limit": 10}
):
    yield event
# Catch GraphRecursionError and emit user-friendly SSE error event
```

**Warning signs:** LangFuse traces with 20+ tool calls; response times >60s; SSE stream that never produces `[DONE]`.

**Phase:** Phase 2 (Agent core) — before any production testing.

---

### Pitfall 3: Playwright Bot Detection on domain.com.au

**What goes wrong:** Headless Chromium fingerprint triggers Cloudflare challenge. Agent receives empty page or challenge HTML, hallucinates data or enters retry loop.

**How to avoid:**
- Use `playwright-stealth` to patch `navigator.webdriver` and User-Agent
- Set realistic Chrome User-Agent
- Randomized delays between requests (1-5s)
- Validate page content before returning to agent:

```python
async def safe_scrape(page, url: str) -> str:
    await page.goto(url, wait_until="networkidle")
    title = await page.title()
    if "just a moment" in title.lower() or "access denied" in title.lower():
        raise BotDetectionError(f"Challenge page detected at {url}")
    return await page.content()
```

**Warning signs:** Pages with title "Just a moment..."; page content < 500 bytes; agent hallucinating property data.

**Phase:** Phase 3 (Playwright scraping) — validate before wiring to agent.

---

### Pitfall 4: MCP Tool Call Failures Not Propagated to LangGraph

**What goes wrong:** Browser timeout or MCP error silently returns empty content to the LLM, or raises unhandled exception that crashes the SSE stream mid-flight.

**How to avoid:**
```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools, handle_tool_errors=True)
```
Wrap MCP tools in a custom class that catches `MCPError`/`TimeoutError` and returns structured error strings rather than raising.

**Warning signs:** SSE stream terminating without `[DONE]` or error message; LangFuse traces ending with no `ai` response.

**Phase:** Phase 3 (Agent + MCP integration) — include failure-path tests.

---

### Pitfall 5: SSE Stream Left Open on Client Disconnect

**What goes wrong:** Browser navigates away; FastAPI generator keeps running — LangGraph, Playwright, and OpenAI all continue consuming resources with no consumer.

**How to avoid:**
```python
async def sse_generator(request: Request, query: str):
    async for event in graph.astream({"messages": [...]}):
        if await request.is_disconnected():
            break
        yield f"data: {json.dumps(event)}\n\n"
    yield "data: [DONE]\n\n"
```
Add hard 120s timeout as secondary defense.

**Warning signs:** Python memory growing after interrupted requests; LangFuse runs outlasting SSE response duration; `asyncio.all_tasks()` count growing.

**Phase:** Phase 4 (API/streaming layer).

---

### Pitfall 6: LangFuse Missing Traces Due to Async Context Propagation

**What goes wrong:** Tool call spans appear as root traces (orphaned) rather than nested under the parent agent trace. `run_in_executor()` does NOT copy `contextvars` context, losing LangFuse trace propagation.

**How to avoid:**
- Always pass `CallbackHandler` explicitly in each invocation config — never set globally:
```python
handler = CallbackHandler(trace_id=trace_id)
async for event in graph.astream(
    {"messages": [HumanMessage(content=query)]},
    config={"callbacks": [handler], "recursion_limit": 10}
):
    yield event
```
- Use native async Playwright (not `run_in_executor`) for anything needing tracing.

**Warning signs:** LangFuse UI showing tool spans as top-level traces; trace count much higher than request count.

**Phase:** Phase 5 (Observability) — verify trace nesting after each integration milestone.

---

### Pitfall 7: Selector Brittleness on domain.com.au Dynamic Content

**What goes wrong:** Generated CSS class names (e.g. `css-1a2b3c`) change on every build deployment. Hard-coded selectors break silently — agent returns empty results or wrong data after a site update.

**How to avoid:**
- Use semantic selectors only: `data-testid`, ARIA roles, semantic HTML elements
- Use `page.get_by_role("article")` for listing cards, `page.get_by_text()` for prices
- Add schema validation: if extracted price is not a number and not "Contact Agent", raise rather than return bad data
- Never hard-code generated class names even during prototyping

**Warning signs:** Agent returning empty lists for queries that previously worked; listings missing prices or addresses; Playwright timeout errors on elements that "should" exist.

**Phase:** Phase 3 (Playwright scraping) — enforce from day one.

---

### Pitfall 8: Blocking Playwright Calls Inside Async FastAPI Route

**What goes wrong:** Any sync Playwright call blocks the entire event loop. All concurrent requests stall.

**How to avoid:**
```python
# WRONG
from playwright.sync_api import sync_playwright

# CORRECT
from playwright.async_api import async_playwright
```
Enable `PYTHONASYNCIODEBUG=1` during development to catch event loop blocks >100ms. Load test with 2 concurrent requests early.

**Phase:** Phase 2/3 (First Playwright integration) — enforce from day one.

---

### Pitfall 9: API Key Leakage Through Git History

**What goes wrong:** `.env` committed before `.gitignore` set up, or keys hard-coded during "quick testing".

**Note:** `LANGFUSE_SECRET_KEY` is always secret despite "public key" naming — both keys together authenticate.

**How to avoid:**
- Add `.env` to `.gitignore` before creating any keys
- Use `pydantic-settings` as single config source
- Set up `pre-commit` with `detect-secrets`
- Use separate LangFuse projects for dev/prod

**Warning signs:** `.env` appearing in `git status` as untracked; `git log --all -S "sk-"` returns commits.

**Phase:** Phase 1 (Foundation) — before any API keys are created.

---

### Pitfall 10: FastAPI SSE CORS Configuration Blocking Browser EventSource

**What goes wrong:** `EventSource` doesn't send preflight; `CORSMiddleware` may not apply CORS headers to `StreamingResponse`. Browser silently fails to receive events.

**How to avoid:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```
Always test SSE from an actual browser (not curl) — CORS issues are invisible in curl.

**Warning signs:** DevTools shows SSE request status 200 but no events; console CORS errors; OPTIONS succeeding but GET `/stream` failing.

**Phase:** Phase 4 (API/streaming layer) — test from browser on day one.

---

### Pitfall 11: LangGraph State Not JSON Serializable for SSE

**What goes wrong:** `BaseMessage` objects in graph state cause `json.dumps()` to fail with `TypeError`, crashing the SSE generator mid-stream.

**How to avoid:**
- Use `astream_events()` (structured event stream) instead of `astream()` — yields pre-formatted dicts easier to serialize
- Use `langchain_core.messages.messages_to_dict()` for message lists
- Validate every SSE event type can `json.loads()` round-trip in tests

**Warning signs:** `TypeError: Object of type HumanMessage is not JSON serializable`; SSE stream stops abruptly; browser receives partial JSON.

**Phase:** Phase 2/4 (Agent + streaming integration).

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase |
|---------|------------------|
| MCP process lifecycle | Phase 1: Foundation |
| API key leakage | Phase 1: Foundation |
| LangGraph recursion limit | Phase 2: Agent core |
| Blocking Playwright in async | Phase 2/3: First Playwright integration |
| LangGraph state serialization | Phase 2/4: Agent + streaming |
| Playwright bot detection | Phase 3: Playwright scraping |
| MCP tool error propagation | Phase 3: Agent + MCP integration |
| Selector brittleness | Phase 3: Playwright scraping |
| SSE client disconnect leak | Phase 4: API/streaming layer |
| CORS for SSE | Phase 4: API/streaming layer |
| LangFuse context propagation | Phase 5: Observability |

---

## "Looks Done But Isn't" Checklist

- [ ] MCP server process starts AND stops cleanly — verify with `ps aux` after FastAPI shutdown
- [ ] Playwright loads a domain.com.au page without bot-block in CI environment
- [ ] Agent handles a tool that always returns empty without running indefinitely
- [ ] Stopping a long SSE request does NOT leave background tasks running
- [ ] All LangFuse tool spans are nested under parent agent trace (not root-level)
- [ ] No `css-` generated class names anywhere in scraping code
- [ ] SSE endpoint works from actual browser `EventSource` (not just curl)
- [ ] `git log --all -S "sk-"` returns nothing
- [ ] `from playwright.sync_api` does not appear in codebase
- [ ] Every SSE event type can be `json.loads()`-ed without error

---

*Pitfalls research for: LangGraph ReAct agent + Playwright MCP + FastAPI SSE + LangFuse + domain.com.au*
*Researched: 2026-02-19*
