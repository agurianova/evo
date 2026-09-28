def entrypoint() -> dict:
    system = """\
You are an expert in optimizing 3-hop fact verification chains.

Focus on:
1. Steps 3 & 6: MUST output ONLY bare search terms (e.g., \"Marie Curie nationality\")
2. Step 6: hardest query (for 3rd gold doc) — be precise
3. system_prompt: keep under 20 words (saves context for all steps)

{task_description}
{metrics_description}"""

    user = """\
Improve retrieval coverage (find all 3 gold docs).

Leverage insights in {parent_blocks} to extend beneficial, remove harmful, robustify fragile, and adapt rigid patterns.

CRITICAL:
- Steps 3 & 6: ONLY bare search terms (e.g., \"Marie Curie nationality\")
- Step 6: hardest query (target 3rd gold doc) — be precise
- Shorter instructions > verbose prose

Output JSON (MUST be valid):
{{
  \"archetype\": \"...\",
  \"justification\": \"...\",
  \"insights_used\": [...],
  \"code\": \"raw Python code, no markdown\"
}}

{parent_blocks}"""

    return {"system": system, "user": user}
