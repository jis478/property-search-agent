"""MCPManager: manages the @playwright/mcp Node.js subprocess lifecycle."""

import asyncio
import logging
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

logger = logging.getLogger(__name__)

MCP_STARTUP_TIMEOUT = 5.0   # seconds — hard fail if not ready within this window
MCP_REQUEST_TIMEOUT = 10.0  # seconds — crash threshold for tool calls
MAX_RESTART_ATTEMPTS = 3


class MCPManager:
    """
    Manages the @playwright/mcp subprocess lifecycle.

    Usage (in FastAPI lifespan):
        manager = MCPManager()
        tools = await manager.start()   # raises RuntimeError on failure
        ...
        await manager.stop()            # clean shutdown + Chromium kill
    """

    def __init__(self) -> None:
        self._client: MultiServerMCPClient | None = None
        self._session_cm = None     # async context manager from client.session()
        self._session = None        # active ClientSession
        self._tools: list[Any] = []
        self._restart_count: int = 0
        self._ready: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_client(self) -> MultiServerMCPClient:
        """Construct a MultiServerMCPClient for the playwright MCP server."""
        return MultiServerMCPClient(
            connections={
                "playwright": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": [
                        "@playwright/mcp",
                        "--headless",    # required: WSL2 has no display server
                        "--no-sandbox",  # required: WSL2 kernel lacks Chrome sandbox
                        "--isolated",    # in-memory profile; no disk state between restarts
                    ],
                }
            }
        )

    async def _ensure_chromium(self) -> None:
        """
        Check whether the Playwright Chromium binary is present.
        If not, run 'npx playwright install chromium' to download it.
        This is a one-time ~100MB download on first startup.
        """
        ms_playwright = Path.home() / ".cache" / "ms-playwright"
        chromium_dirs = list(ms_playwright.glob("chromium-*/chrome-linux/chrome"))
        if chromium_dirs:
            return  # already installed

        logger.warning(
            "Chromium not found — downloading via 'npx playwright install chromium' "
            "(this may take a minute on first run)"
        )
        proc = await asyncio.create_subprocess_exec(
            "npx",
            "playwright",
            "install",
            "chromium",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            output = stdout.decode(errors="replace") if stdout else ""
            raise RuntimeError(
                f"Failed to install Chromium via 'npx playwright install chromium'. "
                f"Output:\n{output}"
            )
        logger.info("Chromium installed successfully")

    def _force_kill_chromium(self) -> None:
        """Last-resort: SIGKILL any remaining chromium processes."""
        try:
            subprocess.run(
                ["pkill", "-9", "-f", "chromium"],
                check=False,
                capture_output=True,
            )
            logger.debug("Force-killed remaining chromium processes")
        except Exception as e:
            logger.debug(f"pkill chromium failed (may already be dead): {e}")

    # ------------------------------------------------------------------
    # Public lifecycle interface
    # ------------------------------------------------------------------

    async def start(self) -> list[Any]:
        """
        Spawn the @playwright/mcp subprocess and load browser tools.

        Returns:
            list[BaseTool] — LangChain-compatible tool objects loaded from MCP.

        Raises:
            RuntimeError: if MCP subprocess fails to start or times out.
        """
        await self._ensure_chromium()

        self._client = self._make_client()
        try:
            self._session_cm = self._client.session("playwright")
            self._session = await asyncio.wait_for(
                self._session_cm.__aenter__(),
                timeout=MCP_STARTUP_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                "MCP subprocess failed — check Node.js and @playwright/mcp installation"
            )
        except Exception as e:
            raise RuntimeError(
                "MCP subprocess failed — check Node.js and @playwright/mcp installation"
            ) from e

        self._tools = await load_mcp_tools(self._session)
        self._ready = True
        self._restart_count = 0
        return self._tools

    async def stop(self) -> None:
        """
        Close the MCP session and ensure Chromium is terminated.
        Best-effort — never raises.
        """
        self._ready = False
        if self._session_cm is not None:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass  # best-effort shutdown
            self._session_cm = None
            self._session = None

        # Give Chromium 2 seconds to exit after session close, then force-kill.
        await asyncio.sleep(2)
        import subprocess as _sp
        result = _sp.run(
            ["pgrep", "-f", "chromium"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            # Chromium still alive — force kill
            self._force_kill_chromium()

    async def _restart(self) -> None:
        """
        Attempt to restart the MCP subprocess after a crash.
        Updates _restart_count and _ready accordingly.
        """
        await self.stop()
        try:
            await self.start()
            logger.info(f"MCP restarted (attempt {self._restart_count + 1})")
        except RuntimeError:
            self._restart_count += 1
            logger.error(
                f"MCP restart {self._restart_count}/{MAX_RESTART_ATTEMPTS} failed"
            )
            if self._restart_count >= MAX_RESTART_ATTEMPTS:
                logger.error("MCP restart attempts exhausted — MCP is down")

    async def call_with_crash_detection(self, coro: Any) -> Any:
        """
        Execute a tool-call coroutine with crash detection.

        Current request always fails on crash — no silent retry.
        A background restart is scheduled for future requests.

        Args:
            coro: awaitable tool-call coroutine

        Returns:
            Result of the coroutine.

        Raises:
            RuntimeError: on timeout, broken pipe, or connection reset.
        """
        try:
            return await asyncio.wait_for(coro, timeout=MCP_REQUEST_TIMEOUT)
        except (asyncio.TimeoutError, BrokenPipeError, ConnectionResetError) as e:
            self._ready = False
            if self._restart_count < MAX_RESTART_ATTEMPTS:
                asyncio.create_task(self._restart())
            raise RuntimeError(f"MCP tool call failed: {e}") from e

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tools(self) -> list[Any]:
        """List of LangChain-compatible browser tools loaded from MCP."""
        return self._tools

    @property
    def ready(self) -> bool:
        """True when the MCP subprocess is running and tools are available."""
        return self._ready
