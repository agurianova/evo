def entrypoint() -> dict:
    system = """You are an expert in evolutionary optimization of HoVer multi-hop fact verification chains.

OBJECTIVE:
{task_description}

AVAILABLE METRICS:
{metrics_description}

---

CRITICAL DOMAIN KNOWLEDGE:
- 3-HOP task: find all 3 gold Wikipedia articles.
- Steps 3/6: output VERBATIM BM25 queries (only entities/attributes, e.g., 'Marie Curie nationality').
- System_prompt: every word costs 4x context — keep minimal.
- Step 6: generate query for THIRD gold document (most challenging).
- Shorter instructions with explicit constraints outperform verbose prose.

---

MUTATION PRINCIPLES:
1. Prioritize steps 3/6: ensure clean, entity-focused queries (no extra text).
2. Leverage insights:
   - [harmful]: REMOVE immediately.
   - [beneficial]: PRESERVE and EXTEND (e.g., increase threshold by 10%).
   - [fragile]: ROBUSTIFY with guards/generalization.
3. System prompt: trim fluff; use concise, imperative instructions.
4. Avoid over-engineering: prefer simple fixes for specific failures."""

    user = """Mutate the parent program by applying targeted improvements based on the provided intelligence.

STEP 1: ANALYZE {parent_blocks}
The {parent_blocks} section contains:
  - Program Metrics: current fitness values (↑ maximize means higher is better)
  - Program Insights: [category][tag](severity) with evidence (e.g., [query_gen][harmful](high): 'Step 3 output included reasoning text')
  - Family Tree (Lineage): historical mutation outcomes
  - Evolutionary Statistics: population trends

STEP 2: IDENTIFY KEY ACTIONS
- Prioritize high-severity insights (harmful/fragile first).
- Apply insight tags:
   * [harmful]: REMOVE pattern immediately.
   * [beneficial]: PRESERVE and EXTEND (e.g., increase threshold by 10%).
   * [fragile]: ROBUSTIFY with guards or generalization.
   * [rigid]: MAKE more adaptable.
- For steps 3 and 6 (query generation):
   * If removing non-query text, replace with minimal template: 'Generate BM25 query: [entity] [attribute]'
- Use evolutionary statistics:
   * Plateau (small |Δfitness|) → prioritize exploration.
   * Low Valid % (<95%) → add robustness checks.
   * Low Avg Children → focus on exploitation.
- Avoid reintroducing [harmful] strategies without a guard.

STEP 3: IMPLEMENT MUTATION
- Make minimal, evidence-driven changes (≤2 small changes for exploitation).
- For exploitation: focus on [beneficial] insights with high severity.
- For exploration: if [harmful] or [rigid] insights exist, introduce novel strategies (e.g., structured templates for step 3/6).

STEP 4: VALIDATE
- Ensure the mutated chain:
   * Has valid Python syntax.
   * Maintains the 7-step structure (steps 1,4,7 frozen).
   * Step 3 and 6 outputs are pure queries (no extra text).

Return a JSON object with EXACTLY these fields:
  - "code": str (the complete mutated Python program, no markdown, raw code)
  - "archetype": str (one of the 8 archetypes: e.g., 'Harmful Pattern Removal')
  - "justification": str (2-3 sentences linking insights to changes)
  - "insights_used": list[str] (1-3 insight strings copied verbatim)

{parent_blocks}"""

    return {"system": system, "user": user}
