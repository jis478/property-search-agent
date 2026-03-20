---
name: run-search
description: Fire a test search query against the running API and pretty-print SSE events
argument-hint: <query>
allowed-tools:
  - Bash
  - AskUserQuestion
---

Fire a test search against the local property search API and stream back results.

## Steps

1. If no query argument was provided, ask the user for one (e.g. "2 bedroom apartment in Richmond under $600/week").

2. POST the query to the search endpoint:
```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "<QUERY>"}'
```
Extract `run_id` from the JSON response.

3. Stream and parse SSE events locally in a single piped command:
```bash
curl -sN http://localhost:8000/stream/<run_id> | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('data:'): continue
    try:
        d = json.loads(line[5:].strip())
    except:
        continue
    t = d.get('type')
    if t == 'step':
        print(f'→ {d.get(\"label\",\"\")}', flush=True)
    elif t == 'complete':
        listings = d.get('listings', [])
        print(f'\nSearch complete — {d.get(\"count\",0)} listings found\n')
        print(f'{'Address':<50} {'Price':<20} {'Beds':>4} {'Baths':>5}  URL')
        print('-'*120)
        for l in listings:
            addr  = (l.get('address') or '')[:48]
            price = (l.get('price') or '')[:18]
            beds  = str(l.get('bedrooms') or '-')
            baths = str(l.get('bathrooms') or '-')
            url   = l.get('listing_url') or ''
            print(f'{addr:<50} {price:<20} {beds:>4} {baths:>5}  {url}')
    elif t == 'error':
        print(f'ERROR: {d.get(\"message\",\"unknown error\")}')
    elif t == 'bot_detected':
        print('WARNING: domain.com.au blocked the scrape (bot detected)')
"
```

The output is parsed locally — only the final formatted table is shown, not the raw SSE stream.

If the server is not running (connection refused), tell the user to start it first with `/dev-server`.
