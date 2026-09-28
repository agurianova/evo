def entrypoint() -> dict:
    system = """You optimize HoVer multi-hop fact verification chains.

OBJECTIVE:
{task_description}

METRICS:
{metrics_description}

MUST:
- Steps 3&6: ONLY query string (no extra text)
- Chain system_prompt: <50 words (repeated 4x)
- Third hop (step6→7) is hardest: target third gold doc

FOCUS MUTATION ON:
1. FIX steps 3/6: remove extra text
2. SHORTEN system_prompt if verbose
3. IMPROVE step6 query using hops 1-2 evidence"""

    user = """Fix critical constraints and improve third-hop retrieval.

Check parent:
- Steps 3&6: must output ONLY query string (remove extra text)
- Chain system_prompt: if >50 words, shorten
- Step6: query must target third gold doc using hops 1-2 evidence

Return valid program. Output JSON: "archetype", "justification", "insights_used", "code".
"code" must be raw Python.

{parent_blocks}"""

    return {"system": system, "user": user}
