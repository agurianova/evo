def entrypoint() -> dict:
    system = """You are evolving HoVer chains for soft retrieval coverage (fraction of 3 gold docs found).

{task_description}

{metrics_description}

**KEY CONSTRAINTS**:
- Steps 3 & 6: PURE BM25 queries ONLY (e.g., 'Marie Curie nationality')
- Step 6 (3rd hop) is hardest: target distantly related doc
- HoVer system_prompt: BE CONCISE (costs 4x context)

**ARCHETYPES** (choose one):
1. Precision Opt: tweak proven patterns
2. Pattern Ext: replicate successes
3. Harmful Rem: remove failures
4. Comp Reinvent: novel paradigms
5. Soln Explore: new strategies
6. Approach Synth: hybrid
7. Guided Innov: preserve + improve
8. Conservative Exp: safe boundaries"""

    user = """EVOLVE: Make ONE strategic mutation using insights.

**INSIGHTS**:
{parent_blocks}

**OUTPUT JSON** (EXACTLY):
- archetype: [one of 8 archetype names]
- justification: 2-3 sentences
- insights_used: [1-3 insight strings]
- code: FULL Python program (raw string, NO markdown)

**CODE RULES**:
- Valid Python: `entrypoint() -> {{'system': str, 'user': str}}`
- Steps 3 & 6: PURE query strings ONLY
- NO extra text in output

**MUST BE VALID JSON, NO OTHER TEXT**"""

    return {"system": system, "user": user}
