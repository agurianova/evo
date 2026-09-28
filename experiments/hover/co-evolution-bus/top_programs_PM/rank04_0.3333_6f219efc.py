def entrypoint() -> dict:
    system = """You are an expert in evolving HoVer multi-hop fact verification chains. Your mutations must strictly improve soft retrieval coverage.

CRITICAL CONSTRAINTS:
- Steps 3 & 6: Output MUST be pure BM25 queries (e.g., "Marie Curie nationality", NOT prose). Any extra text breaks retrieval.
- system_prompt: Every word is multiplied by 4 (used in 4 steps). Keep it minimal (≤50 words).
- 3-hop requirement: Step 6 query must find the 3rd gold document (most challenging).

OPTIMIZE FOR: {metrics_description}

This system prompt is {task_description}"""
    user = """Analyze the {parent_blocks} section below. Then:

1. **IMMEDIATELY REMOVE** any [harmful] pattern (especially in steps 3/6: non-query text; or system_prompt verbosity). Example:
   - Bad step3 output: "Based on the evidence, the query is: Marie Curie nationality" → MUST become "Marie Curie nationality"
   - Bad system_prompt: >50 words → trim to essential imperatives.

2. **IF PLATEAUING** (recent |Δfitness| < 0.05):
   - Prioritize EXPLORATION in query generation (steps 3/6): try novel query templates (e.g., structured as [subject] [relation] [object]) but ensure pure text.
   - Avoid repeating strategies that recently caused [harmful] outcomes.

3. **RETURN** a JSON with:
   - "code": [mutated program as raw Python string]
   - "archetype": [one of 8 archetypes, e.g., "Harmful Pattern Removal"]
   - "justification": [2-3 sentences linking changes to insights]
   - "insights_used": [list of 1-3 insight strings]

{parent_blocks}"""
    return {"system": system, "user": user}
