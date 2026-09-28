#!/usr/bin/env python3
"""Quick reasoning quality check for the 3 mutation servers."""

import json
import urllib.request

SERVERS = {
    "A (10.226.72.211)": "http://10.226.72.211:8777/v1",
    "B (10.226.15.38)": "http://10.226.15.38:8777/v1",
    "C (10.226.185.131)": "http://10.226.185.131:8777/v1",
    "D (10.225.51.251)": "http://10.225.51.251:8777/v1",
}

PROMPT = "Write a Python function that reverses a string."

PAYLOAD = json.dumps(
    {
        "model": "Qwen3-235B-A22B-Thinking-2507",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 500,
        "temperature": 0.6,
    }
).encode()

for name, base_url in SERVERS.items():
    print(f"\n{'=' * 60}")
    print(f"Server {name}")
    print(f"{'=' * 60}")
    try:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=PAYLOAD,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        choice = data["choices"][0]
        message = choice["message"]
        reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
        content = message.get("content") or ""
        finish = choice.get("finish_reason", "?")
        usage = data.get("usage", {})

        print(f"  reasoning chars : {len(reasoning)}")
        print(f"  content chars   : {len(content)}")
        print(f"  finish_reason   : {finish}")
        print(f"  prompt tokens   : {usage.get('prompt_tokens', '?')}")
        print(f"  completion tokens: {usage.get('completion_tokens', '?')}")
        print(f"  reasoning fields: {[k for k in message if 'reason' in k.lower()]}")
        print("  --- reasoning (first 300 chars) ---")
        print(f"  {reasoning[:300]!r}")
    except Exception as e:
        print(f"  ERROR: {e}")
