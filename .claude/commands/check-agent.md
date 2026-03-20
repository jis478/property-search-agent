---
name: check-agent
description: Inspect registered MCP tools, agent health, and LangGraph graph structure
allowed-tools:
  - Bash
---

Inspect the running property search agent — MCP tools, health, and graph.

## Steps

1. Check server health:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

2. List all registered MCP tools:
```bash
curl -s http://localhost:8000/tools | python3 -m json.tool
```
Print the count and each tool name + description.

3. Show the LangGraph graph structure by reading the source:
- `agent/__init__.py` — property search agent (ReAct)
- `agent/chat_graph.py` — chat workflow (async/sync tool routing)

Summarise:
- How many tools are registered
- Which tools are async vs sync in the chat graph
- Whether MCP is `ready` or `degraded`

If the server is not running, tell the user to start it with `/dev-server`.
