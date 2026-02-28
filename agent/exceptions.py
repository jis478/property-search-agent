class PropertyAgentError(Exception):
    """Base class for all property agent errors."""

class BotDetectedError(PropertyAgentError):
    """domain.com.au returned a bot-challenge or CAPTCHA page."""

class StepLimitError(PropertyAgentError):
    """Agent hit the LangGraph recursion_limit without completing."""

class MCPError(PropertyAgentError):
    """Playwright MCP subprocess crashed or became unresponsive."""
