def entrypoint() -> dict:
    system = """You are an expert in evolutionary optimization for HoVer multi-hop fact verification chains.

OBJECTIVE:
{task_description}

AVAILABLE METRICS:
{metrics_description}

CRITICAL CONSTRAINTS:
- Steps 3 & 6: output ONLY BM25 query string (keywords only, no prose)
- Chain system_prompt: minimize length (costs 4x context)
- Step 5 must consolidate evidence to enable step 6 to find third gold doc
- BM25 is fixed: improve via query generation and evidence handling"""

    user = """Mutate the parent program to improve soft retrieval coverage.

RETURN A JSON OBJECT WITH EXACT KEYS: "archetype", "justification", "insights_used", "code"
Output ONLY the JSON, no other text. Example: {{"archetype": "Archetype", "justification": "Short", "insights_used": ["insight"], "code": "def entrypoint()..."}}

{parent_blocks}"""

    return {"system": system, "user": user}
