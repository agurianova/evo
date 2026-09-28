def entrypoint() -> dict:
    system = """You are an expert in evolving HoVer chains ({task_description}). CRITICAL:
- Steps 3/6: Pure BM25 queries only (e.g., 'Marie Curie nationality'). No extra text.
- system_prompt: <=50 words (multiplied by 4 steps).
- Step 6 query must find the 3rd gold document.

OPTIMIZE FOR: {metrics_description}"""
    user = """Analyze the {parent_blocks} section below. Then:

1. **REMOVE HARMFUL PATTERNS** with specific checks:
   - Steps 3 & 6: Output must be pure BM25 query (single line, no punctuation except spaces).
     Remove any non-query text (e.g., colons, quotes, or phrases like "Based on evidence").
     Validate: only alphanumeric and spaces allowed (regex: ^[a-zA-Z0-9 ]+$).
   - HoVer chain's system_prompt: Must be <=50 words and a fixed string (no placeholders). Remove any non-essential words and any placeholder references (e.g., {{task_description}}).
   - Step 5: Must extract key entities and relations for step 6 query generation.

2. **IF PLATEAUING** (defined as: last 3 generations show average fitness change < 0.05):
   - Prioritize EXPLORATION in steps 3/6: generate queries using one of these strategies (choose based on step5 evidence):
        Strategy 1 (Entity-focused): e.g., 'Marie Curie nationality'
        Strategy 2 (Relation-paraphrased): e.g., 'Eiffel Tower location Paris'
        Strategy 3 (Attribute-based): e.g., 'birthplace of Marie Curie'
   - Avoid strategies recently tagged [harmful] in lineage.

3. **RETURN** raw JSON (no markdown) with:
   - "code": [mutated program as raw Python string]
   - "archetype": [one of 8 archetypes, e.g., "Approach Synthesis"]
   - "justification": [2-3 sentences linking changes to insights]
   - "insights_used": [list of 1-3 insight category strings, e.g., "harmful_pattern_recognition"]

{parent_blocks}"""
    return {"system": system, "user": user}
