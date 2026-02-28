"""Agent orchestration package — public API for Phase 4 import.

Phase 4 SSE endpoints import from here:
    from agent import build_agent, search_properties, PropertyListing, BotDetectedError
"""
from agent.property_agent import build_agent, search_properties
from agent.models import PropertyListing
from agent.exceptions import (
    PropertyAgentError,
    BotDetectedError,
    StepLimitError,
    MCPError,
)

__all__ = [
    "build_agent",
    "search_properties",
    "PropertyListing",
    "PropertyAgentError",
    "BotDetectedError",
    "StepLimitError",
    "MCPError",
]
