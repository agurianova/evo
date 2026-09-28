def entrypoint() -> dict:
    system = """HoVer chain optimizer.

OBJECTIVE: {task_description}
METRICS: {metrics_description}

MUST:
- Steps 3,6: ONLY query string
- system_prompt: <50 words
- Step6: target third gold doc

Focus on these."""
    user = """Fix parent:
- Steps 3,6: stage_action must be ONLY query string
- system_prompt: if >50 words, shorten
- Step6: query uses hops 1-2 evidence for third gold doc

Output JSON: "code", "archetype", "justification", "insights_used".
"code" is raw Python.

{parent_blocks}"""
    return {"system": system, "user": user}
