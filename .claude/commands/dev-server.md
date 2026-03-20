---
name: dev-server
description: Start the FastAPI app with hot reload and tail logs
allowed-tools:
  - Bash
---

Start the local property search API server.

## Steps

1. Check if the server is already running:
```bash
curl -s http://localhost:8000/health
```
If it responds, tell the user the server is already up and show the health status.

2. If not running, start it with uvicorn hot-reload from the project root:
```bash
cd /home/mark/hobby && /home/mark/miniconda3/envs/rental-search/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run this in the foreground so logs stream to the terminal. The server is ready when you see `MCP ready` in the output.

Note: The MCP subprocess requires Node.js and `@playwright/mcp` to be installed. If startup fails with an MCP error, check that `node` is on PATH and `node_modules` exists in the project root.
