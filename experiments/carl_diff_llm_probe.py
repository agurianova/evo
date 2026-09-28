"""Live structured-output probe for the CARL DAG-diff schema (design S4.6, probe 1+2).

Asks the proxy mutator model for chain mutations under two enforcement modes:
  json_schema  -- response_format guided decoding (grammar-constrained if vLLM supports it)
  tools        -- function_calling (schema shown to the model, not grammar-enforced)
Every reply is pushed through TypeAdapter -> apply_diff -> ReasoningChain round-trip,
so the numbers reported are end-to-end genome validity, not just JSON well-formedness.

Run: NO_PROXY="$NO_PROXY,10.232.89.98" \
     /home/jovyan/.mlspace/envs/evo/bin/python3 experiments/carl_diff_llm_probe.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import time

from openai import AsyncOpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carl_diff_prototype as proto  # noqa: E402
from mmar_carl.chain import ReasoningChain  # noqa: E402
from pydantic import ValidationError  # noqa: E402

BASE_URL = "http://10.232.89.98:4000/v1"
MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"
MAX_CONCURRENT = 4

SYSTEM = """You mutate CARL reasoning chains (DAGs of LLM steps) to improve a one-sentence summarizer.

You must output a chain-diff in the positional-slot language:
- Pick base_parent ("A" or "B"). You may only keep steps by ids belonging to that parent.
- "steps" is the FULL child chain as an ordered list of 1..8 slots. Omitting a base step deletes it.
- Each slot is either {"kind": "keep", "id": <base step id>, "edits": {...partial field overrides...}}
  or {"kind": "new", "title": ..., "aim": ..., "stage_action": ..., "reasoning_questions": ...}.
- Every slot after the first must declare "dependencies": a list of earlier slots ("slot_1".."slot_<k-1>")
  whose outputs it consumes. Slot 1 takes no dependencies field. Repeating a keep id duplicates that step.
- The final slot is the output step; its answer is scored by ROUGE-L against a reference summary.
- Fill "reasoning" with one short sentence on why the mutation should help."""

INTENTS = [
    (
        "insert",
        "Insert a fact-verification step between drafting and polishing in parent A.",
    ),
    (
        "delete",
        "Remove one step to make the cheapest chain you believe still scores well.",
    ),
    (
        "rewire",
        "Restructure parent B so two of its steps run in parallel directly off the raw input.",
    ),
    (
        "edit",
        "Keep parent A's structure but rewrite the aims to be sharper about language fidelity.",
    ),
    ("rewrite", "Design a fresh 4-step chain from scratch (all-new steps)."),
    (
        "duplicate",
        "Produce two independent draft candidates, then a final step that polishes the better one.",
    ),
    (
        "grow",
        "Grow the chain to at least 5 steps with an extract/branch/merge structure.",
    ),
    ("free", "Improve either parent however you see fit for the ROUGE-L objective."),
]


def user_prompt(bases: dict[str, ReasoningChain], intent: str) -> str:
    parents = "\n\n".join(
        f"[parent {ns}]\n{proto.render_for_prompt(ns, ch)}" for ns, ch in bases.items()
    )
    return f"{parents}\n\nMutation request: {intent}\nOutput only the diff."


def check(payload_text: str, adapter, bases, extras) -> tuple[str, str]:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as e:
        return "json_error", str(e)[:120]
    try:
        diff = adapter.validate_python(payload)
    except ValidationError as e:
        first = e.errors()[0]
        return (
            "schema_error",
            f"{e.error_count()} errors; first: {first['loc']} {first['msg']}"[:160],
        )
    try:
        wire = proto.apply_diff(diff, bases, extras)
        proto.assert_valid_genome(wire)
    except Exception as e:
        return "apply_error", str(e)[:160]
    shape = " | ".join(
        f"{s['number']}:{s['title'][:20]!r}<-{s['dependencies']}" for s in wire["steps"]
    )
    return "ok", f"base={diff.base_parent} {shape}"


async def call_one(
    client, sem, mode: str, tag: str, intent: str, schema: dict, adapter, bases, extras
) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_prompt(bases, intent)},
    ]
    kwargs: dict = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 4096,
        "timeout": 180,
    }
    if mode == "json_schema":
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "chain_dag_diff", "schema": schema},
        }
    else:
        kwargs["tools"] = [
            {
                "type": "function",
                "function": {"name": "emit_chain_diff", "parameters": schema},
            }
        ]
        kwargs["tool_choice"] = {
            "type": "function",
            "function": {"name": "emit_chain_diff"},
        }
    async with sem:
        t0 = time.monotonic()
        try:
            resp = await client.chat.completions.create(**kwargs)
        except Exception as e:
            return {
                "mode": mode,
                "tag": tag,
                "status": "call_error",
                "detail": str(e)[:200],
                "secs": round(time.monotonic() - t0, 1),
            }
        secs = round(time.monotonic() - t0, 1)
    msg = resp.choices[0].message
    if mode == "tools":
        if not msg.tool_calls:
            return {
                "mode": mode,
                "tag": tag,
                "status": "no_tool_call",
                "detail": (msg.content or "")[:120],
                "secs": secs,
            }
        text = msg.tool_calls[0].function.arguments
    else:
        text = msg.content or ""
    status, detail = check(text, adapter, bases, extras)
    return {"mode": mode, "tag": tag, "status": status, "detail": detail, "secs": secs}


async def main() -> None:
    seeds = {
        "A": json.loads((proto.PACK_CHAINS / "chain_2step.json").read_text()),
        "B": json.loads((proto.PACK_CHAINS / "chain_3step.json").read_text()),
    }
    bases = {
        ns: ReasoningChain.from_dict(d, use_typed_steps=True) for ns, d in seeds.items()
    }
    extras = {ns: d["task_description"] for ns, d in seeds.items()}
    adapter = proto.build_diff_model(bases)
    schema = adapter.json_schema()
    print(
        f"model={MODEL}  schema_bytes={len(json.dumps(schema))}  intents={len(INTENTS)}"
    )

    client = AsyncOpenAI(base_url=BASE_URL, api_key="sk-gigaevo")
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = [
        call_one(client, sem, mode, tag, intent, schema, adapter, bases, extras)
        for mode in ("json_schema", "tools")
        for tag, intent in INTENTS
    ]
    results = await asyncio.gather(*tasks)

    for mode in ("json_schema", "tools"):
        rows = [r for r in results if r["mode"] == mode]
        ok = sum(r["status"] == "ok" for r in rows)
        print(f"\n== mode={mode}: {ok}/{len(rows)} valid genomes ==")
        for r in rows:
            print(
                f"  [{r['status']:<12}] {r['tag']:<10} {r['secs']:>6}s  {r['detail']}"
            )


if __name__ == "__main__":
    asyncio.run(main())
