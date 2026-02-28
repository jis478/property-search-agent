#!/usr/bin/env python3
"""Integration smoke test for the LangGraph property search agent.

Usage: conda run -n rental-search python scripts/test_agent.py
"""
import asyncio
import sys
import traceback

# Ensure project root is on sys.path when running from scripts/ directory
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_subprocess.manager import MCPManager
from agent import build_agent, search_properties
from agent.exceptions import BotDetectedError, StepLimitError

QUERY = "2 bedroom apartments in Richmond VIC under $800 per week"

async def main():
    manager = MCPManager()
    try:
        print("Starting MCPManager...")
        mcp_tools = await manager.start()
        print(f"MCP ready — {len(mcp_tools)} tools available")

        agent = build_agent(mcp_tools)
        print(f"Agent built. Running query: {QUERY!r}")
        print("-" * 60)

        listings = await search_properties(agent, QUERY)

        print(f"Found {len(listings)} listings across up to 3 pages:")
        print("-" * 60)
        for i, listing in enumerate(listings, 1):
            print(f"[{i}] {listing.model_dump()}")

    except BotDetectedError as e:
        print(f"BOT DETECTED: {e}", file=sys.stderr)
        sys.exit(1)
    except StepLimitError as e:
        print(f"STEP LIMIT: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
    finally:
        await manager.stop()
        print("MCPManager stopped.")

if __name__ == "__main__":
    asyncio.run(main())
