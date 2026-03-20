---
name: lint
description: Run linting and type checks across the Python codebase
allowed-tools:
  - Bash
---

Run linting and static analysis on the project Python source.

## Steps

1. Run ruff (fast linter) if available, otherwise fall back to flake8:
```bash
cd /home/mark/hobby && python3 -m ruff check . --exclude node_modules 2>/dev/null || python3 -m flake8 . --exclude=node_modules,__pycache__,.venv
```

2. Run mypy type checks on the main modules:
```bash
cd /home/mark/hobby && python3 -m mypy agent/ api/ main.py config.py --ignore-missing-imports 2>/dev/null || echo "mypy not installed"
```

3. Summarise results:
   - Total errors/warnings per tool
   - List any files with issues
   - If clean, confirm "No lint issues found"

Fix any issues found if the user asks, otherwise just report them.
