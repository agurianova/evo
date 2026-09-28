def entrypoint() -> dict:
    system = """\
You are an expert in evolutionary optimization for HoVer chains.

OBJECTIVE:
{task_description}

AVAILABLE METRICS:
{metrics_description}

---

MUTATION PRINCIPLES:
1. Steps 3/6: PURE BM25 queries only (e.g., 'Marie Curie nationality') — NO extra text.
2. Prioritize step 6 (third-hop) — bottleneck for 3/3 coverage.
3. Brevity: system_prompt used 4x → keep step aims <15 words.
4. Fixed steps: no reordering. Diversity only in content (e.g., reasoning questions).
5. Fix harmful patterns; preserve beneficial ones."""

    user = """\
Mutate to fix constraints and improve step 6.

Before writing code:
1. Remove harmful patterns (e.g., missing step constraints).
2. Focus on step 6 (third-hop query) — current bottleneck.
3. Steps 3/6: output ONLY BM25 query (one line).
4. Keep instructions concise (system_prompt used 4x).

Produce a program that adheres to HoVer constraints.

Return JSON: "archetype", "justification", "insights_used", "code".
"code" must be valid Python (no markdown).

{parent_blocks}"""

    return {"system": system, "user": user}
