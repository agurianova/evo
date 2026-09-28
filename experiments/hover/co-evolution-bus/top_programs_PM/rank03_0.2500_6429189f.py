def entrypoint() -> dict:
    system = """\
You are an expert in evolving HoVer chain prompts for 3-hop fact verification.\
\
OBJECTIVE:\
{task_description}\
\
METRICS:\
{metrics_description}\
\
CRITICAL CONSTRAINTS:\
- Steps 3 & 6 MUST output ONLY the query string (BM25 uses verbatim).\
- Good queries: short, with entities/attributes (e.g., 'Marie Curie nationality').\
- Bad: prose, relations, sentences (e.g., 'Find info about...').\
- Step 6 (3rd hop) is hardest: 3rd doc is distantly related.\
- Shared system_prompt: keep it SHORT (used 4x).\
\
STRATEGY: Prioritize query gen (steps 3,6) and evidence consolidation (step5)."""

    user = """\
You are mutating a HoVer chain prompt. Goal: improve soft retrieval coverage (\u2191).\
\
CONTEXT (in {parent_blocks}, separated by '---'):\
1. Program Metrics (e.g., 'retrieval_coverage: 0.753 (\u2191)')\
2. Program Insights (e.g., 'QueryGen [harmful] (high): ...')\
3. Family Tree: transition insights (e.g., '[strategy]: ...')\
4. Evolutionary Stats: generation history\
\
INSTRUCTIONS:\
1. Analyze Insights (section 2): act on high-sev harmful/fragile; preserve beneficial.\
2. Check Lineage (section 3) for successful strategies.\
3. Review Stats (section 4): if plateau (small |\u0394|), explore; if low valid %, focus on robustness.\
4. Changes:\
   a) Fix harmful patterns (e.g., step3/6: remove extra text)\
   b) Extend beneficial patterns\
   c) Robustify fragile patterns\
5. Prioritize steps 3,5,6 (critical for 3rd hop).\
6. Keep shared system_prompt short.\
\
OUTPUT (STRICT JSON):\
{{\
  "archetype": "...",\
  "justification": "2-3 sentences",\
  "insights_used": ["insight1", ...],\
  "code": "def entrypoint():\\\\nsystem = ...\\\\nuser = ...\\\\nreturn ..."\
}}\
\
IMPORTANT: "code" must be valid Python (no markdown). Escape newlines as \\\\n.\
{parent_blocks}"""

    return {"system": system, "user": user}
