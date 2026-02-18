# Domain Property Search Agent

## What This Is

A LangGraph ReAct agent that accepts natural-language property search requests and uses a Playwright MCP server to browse domain.com.au, extract matching listings, and stream the results back to the user. A FastAPI backend serves both the agent API and a minimal web UI, with LangFuse providing full observability into every agent run.

## Core Value

The agent autonomously navigates domain.com.au on behalf of the user and returns structured property listings — the browser automation must work reliably and results must appear in the UI.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can type a natural-language property search request into the web UI
- [ ] LangGraph ReAct agent (GPT-4o) processes the request and plans tool use
- [ ] Agent uses Playwright MCP server to navigate and search domain.com.au
- [ ] Agent extracts listing details: address, price, bedrooms, bathrooms, listing URL
- [ ] Frontend streams agent thinking and tool call steps in real-time
- [ ] Frontend displays structured listing cards after agent completes
- [ ] LangFuse traces all agent runs (inputs, tool calls, outputs, latency)

### Out of Scope

- Mobile app — web-first only
- User authentication — single-user local tool
- Saving/persisting search history — stateless per request
- Other property sites — domain.com.au only for v1

## Context

- Python backend with LangGraph for agent orchestration
- OpenAI GPT-4o as the LLM powering the ReAct agent
- Playwright MCP server provides browser automation tools to the agent
- FastAPI serves both the REST/streaming API and the static frontend page
- LangFuse for tracing (Python SDK)
- Frontend is a single HTML page — no build step, served directly by FastAPI
- Streaming uses Server-Sent Events (SSE) to push agent steps to the browser

## Constraints

- **Tech Stack**: Python, LangGraph, FastAPI, Playwright MCP, LangFuse, OpenAI GPT-4o
- **Frontend**: Single HTML file served by FastAPI — no Node/npm build step
- **Browser**: Playwright runs headless (or headed for debugging)
- **Scope**: domain.com.au only — no generalised browser agent for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph ReAct agent | Standard pattern for tool-using agents with explicit reasoning steps | — Pending |
| Playwright MCP server | Gives the agent browser control via the MCP protocol | — Pending |
| FastAPI + SSE for streaming | Simple, no WebSocket complexity, works natively in browsers | — Pending |
| LangFuse for tracing | Purpose-built LLM observability, easy Python SDK integration | — Pending |

---
*Last updated: 2026-02-19 after initialization*
