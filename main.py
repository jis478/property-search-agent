from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from config import settings  # noqa: F401 — ensures settings loaded and validated at startup

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2 will add MCP subprocess startup here
    yield
    # Phase 2 will add MCP subprocess shutdown here


app = FastAPI(
    title="Property Search Agent",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")
