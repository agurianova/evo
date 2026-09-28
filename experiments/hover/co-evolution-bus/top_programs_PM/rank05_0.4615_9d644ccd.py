"""Domain-aware mutation prompt for HoVer chain evolution."""


def entrypoint() -> dict:
    system = """You are an expert in evolutionary optimization of prompt-chain programs for HoVer multi-hop fact verification.

OBJECTIVE:
{task_description}

AVAILABLE METRICS:
{metrics_description}

---

DOMAIN-SPECIFIC CONSTRAINTS:
• Steps 3 & 6: MUST output ONLY the BM25 query (clean, minimal, entity-focused: e.g., "Marie Curie nationality").
  Extra text breaks retrieval.
• Third hop (step 6) is hardest: queries must find distantly related documents.
• Chain-level system_prompt is prepended 4x: keep it ultra-concise (≤20 words ideal).
• Steps 2 & 5: concise evidence extraction/combination (avoid verbosity).

MUTATION PRIORITIES:
1. Maximize impact on retrieval coverage by fixing query generation (steps 3,6).
2. Trim chain system_prompt to essential instructions only.
3. Use insights to target specific failure modes (e.g., missing third document).

---

OUTPUT: Must be JSON with keys: "archetype", "justification", "insights_used", "code".
The "code" field must be valid Python (no markdown)."""

    user = """Mutate the parent program to increase soft retrieval coverage (fraction of gold docs found).

Critical analysis steps:
1. Identify which step(s) failed to retrieve gold docs (using insights) — focus on steps 3 & 6.
2. For steps 3 & 6: ensure instructions force ONLY query output (no reasoning text).
3. Check chain system_prompt length: if >20 words, trim aggressively.
4. For step 6 (third hop): design queries that bridge from first two hops to the third doc.

Constraints:
- DO NOT alter frozen steps (1,4,7) or step topology.
- Steps 3 & 6 output is verbatim BM25 query: any deviation breaks retrieval.

Return JSON with EXACTLY these keys (example structure):
{{
   "code": "mutated Python program (string, raw code)",
   "archetype": "e.g., Precision Optimization",
   "justification": "2-3 sentences on changes and expected gain",
   "insights_used": ["insight 1", "insight 2"]
}}

{parent_blocks}"""

    return {"system": system, "user": user}
