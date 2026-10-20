"""Sample inputs for the mock /analyze endpoint.

Run with the dev server up:
    uv run python scripts/seed_mock.py
"""

import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8000/analyze",
    data=json.dumps({"text": "Transformer models have transformed NLP."}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req) as resp:
    print(json.dumps(json.loads(resp.read()), indent=2))