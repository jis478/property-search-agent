---
name: test-enrichment
description: Test school-distance enrichment with sample listings and a school address
argument-hint: [school address]
allowed-tools:
  - Bash
  - AskUserQuestion
---

Test the school-distance enrichment pipeline (agent/enrichment.py) directly without running a full search.

## Steps

1. Check that GOOGLE_MAPS_API_KEY is set:
```bash
grep -i google_maps /home/mark/hobby/.env 2>/dev/null || echo "not set"
```
If missing or empty, warn the user that enrichment will be skipped and they need to add `GOOGLE_MAPS_API_KEY=<key>` to `.env`.

2. If no school address argument was provided, use a default: `"Richmond Primary School, Richmond VIC"`.

3. Run a quick enrichment smoke test using a small set of fake listings:
```bash
cd /home/mark/hobby && python3 - <<'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
from agent.models import PropertyListing
from agent.enrichment import enrich_listings_with_school_distance

api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
if not api_key:
    print("ERROR: GOOGLE_MAPS_API_KEY not set")
    exit(1)

listings = [
    PropertyListing(address="123 Church St, Richmond VIC 3121", price="$550/week", bedrooms=2),
    PropertyListing(address="456 Swan St, Richmond VIC 3121", price="$580/week", bedrooms=2),
    PropertyListing(address="789 Bridge Rd, Richmond VIC 3121", price="$600/week", bedrooms=2),
]

school = "Richmond Primary School, Richmond VIC"
result = enrich_listings_with_school_distance(listings, school, max_distance_meters=1500, api_key=api_key)

print(f"\nInput:  {len(listings)} listings")
print(f"Output: {len(result)} listings within 1500m of {school}\n")
for l in result:
    print(f"  {l.address} — {l.distance_to_school}m")
EOF
```

4. Report whether enrichment worked, how many listings passed the distance filter, and any errors.
