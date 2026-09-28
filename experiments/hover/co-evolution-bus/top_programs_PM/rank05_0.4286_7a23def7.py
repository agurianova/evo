def entrypoint() -> dict:
    system = "{task_description}\n{metrics_description}\nCRITICAL: Steps 3/6: ONLY BM25 queries (e.g., 'X Y'). No prose. Step 6 hardest. SYSTEM_PROMPT: 4x cost — keep minimal."

    user = """EVOLUTIONARY MUTATION: HoVer Chain

{parent_blocks}

- Steps 3/6: OUTPUT ONLY BM25 queries (e.g., 'X Y'). NO PROSE.
- Plateau? (|Δfitness|<0.05 in last 3 gens) → EXPLORATION.
- HIGH-SEVERITY harmful insights: PRIORITY (e.g., step 6 neglect → fix step 6).

## ARCHETYPES
1. Step6_Query_Opt: Fine-tune step 6 query
2. Step5_Evidence_Improve: Better step 5 for step 6
3. Remove_Prose: Eliminate non-query text in steps 3/6
4. Novel_Queries: New step 6 query structures
5. Alt_Evidence_Synthesis: Change step 5 combo
6. Step6_Validation: Enforce pure query in step 6
7. Guided_Step6: Preserve + improve step 6
8. Safe_Exploration: Query exploration within bounds

## EXAMPLE (step 6)
Orig: \"Generate BM25 query\"
Mut: \"Output ONLY: 'X Y'\"

## OUTPUT
ONLY JSON: {{\"archetype\":\"...\", \"just\":\"...\", \"insights\":[\"...\"], \"code\":\"...\"}}"""

    return {"system": system, "user": user}
