import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from config import settings  # noqa: F401 — ensures settings loaded and validated at startup
from mcp_subprocess.manager import MCPManager
from agent import build_agent
from api.search import router as search_router
from api.stream import router as stream_router

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    manager = MCPManager()
    try:
        tools = await manager.start()
    except RuntimeError as e:
        logger.error("ERROR: MCP subprocess failed — check Node.js and @playwright/mcp installation")
        raise  # Hard fail: FastAPI refuses to start; process exits non-zero

    app.state.mcp_manager = manager
    app.state.mcp_tools = tools
    app.state.agent = build_agent(tools)
    logger.info("LangGraph agent built and stored on app.state")

    tool_names = [t.name for t in tools]
    logger.info(f"MCP ready — {len(tools)} tools available")
    logger.debug(f"MCP tools: {tool_names}")

    yield

    # === SHUTDOWN ===
    await manager.stop()
    logger.info("MCP subprocess shut down cleanly")


app = FastAPI(
    title="Property Search Agent",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Cache-Control", "X-Accel-Buffering"],
)

app.include_router(search_router)
app.include_router(stream_router)


@app.get("/health")
async def health(request: Request):
    manager: MCPManager = request.app.state.mcp_manager
    if manager.ready:
        return {"status": "ok", "mcp": "ready"}
    return JSONResponse(
        status_code=200,  # always 200 — degraded is a status field, not HTTP 5xx
        content={"status": "degraded", "mcp": "down"},
    )


@app.get("/tools")
async def list_tools(request: Request):
    tool_list = request.app.state.mcp_tools
    return {
        "count": len(tool_list),
        "tools": [{"name": t.name, "description": t.description} for t in tool_list],
    }


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")
