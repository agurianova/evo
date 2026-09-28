def entrypoint() -> dict:
    system = """\
You are an expert in optimizing multi-hop fact verification chains for the HoVer task.

OBJECTIVE:
{task_description}

AVAILABLE METRICS:
{metrics_description}

CRITICAL DOMAIN KNOWLEDGE FOR HOVER CHAINS:
- This is a 3-HOP retrieval task: the chain must find ALL 3 gold Wikipedia articles.
- Steps 3 and 6 (query generation) must output VERBATIM BM25 queries: only named entities and key attributes (e.g., "Marie Curie nationality"), NO prose or reasoning.
- BM25 is bag-of-words: queries should be short, keyword-based, and avoid relation words.
- The system_prompt (shared by all LLM steps) is prepended 4x: every word costs context 4x → keep it extremely concise.
- Step 5 consolidates evidence from hops 1 and 2; Step 6 must generate a query for the THIRD gold document (the most challenging).
- Shorter instructions with explicit constraints outperform verbose prose.

MUTATION PRINCIPLES:
1. Prioritize fixing violations of critical domain knowledge (e.g., prose in query steps, long system_prompt).
2. When modifying step instructions, focus on making them explicit, constraint-driven, and minimal.
3. If a step is frozen (like BM25 tools), do not change it — focus only on evolvable LLM steps (2,3,5,6).
4. Always validate that step 3 and 6 outputs are clean BM25 queries (no extra text)."""

    user = """\
Mutate the parent program to improve soft retrieval coverage on the HoVer task.

BEFORE WRITING CODE:
1. Analyze the parent chain for violations of CRITICAL DOMAIN KNOWLEDGE (see system prompt):
   - Check step 3 and 6: do they output only a clean BM25 query? If not, fix by making instructions explicit.
   - Check system_prompt length: if verbose, shorten while preserving key constraints.
   - Check step 5: does it effectively combine evidence for step 6 to generate the third-hop query?
2. Use the provided insights and failure analysis to guide changes.
3. Focus on the most critical violations first (high severity).

AFTER ANALYSIS, PRODUCE A MUTATED PROGRAM THAT:
- Fixes the top 1-2 critical violations found.
- Preserves what works (if a step has high beneficial insights, do not change it unnecessarily).
- Is syntactically valid and maintains the same chain structure.

RETURN A JSON OBJECT WITH THESE KEYS:
{{
    "code": "Complete mutated Python program (raw code, no markdown)",
    "archetype": "Name of the mutation strategy used (e.g., 'Computational Reinvention')",
    "justification": "2-3 sentences explaining the changes and why they should improve coverage",
    "insights_used": ["list", "of", "insight", "strings", "used"]
}}

IMPORTANT: The "code" field must be valid Python code that defines an entrypoint() function returning a dict with "system" and "user" strings.

{parent_blocks}"""

    return {"system": system, "user": user}
