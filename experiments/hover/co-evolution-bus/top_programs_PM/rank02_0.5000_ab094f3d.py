"""Mutated prompt: HoVer-specific mutation strategy with step-targeted archetypes and third-hop focus."""


def entrypoint() -> dict:
    system = """You are an expert in evolutionary optimization of prompt-chain programs for the HoVer multi-hop fact verification task.

    OBJECTIVE:
    {task_description}

    AVAILABLE METRICS:
    {metrics_description}

    DOMAIN KNOWLEDGE:
    - This is a 3-hop retrieval task: the chain must find 3 gold Wikipedia articles (one per hop).
    - Steps 3 and 6 generate BM25 queries that are used VERBATIM (no prose allowed).
    - Good queries: short, focused on named entities and key attributes (e.g., \"Marie Curie nationality\").
    - Bad queries: prose, relation words, sentence structure (e.g., \"Find information about Marie Curie's national origin.\").
    - Step 6 (third hop) is the most challenging because the third gold document is distantly related.
    - system_prompt is shared by all 4 LLM steps — every word costs context 4x.

    MUTATION STRATEGY:
    1. STEP 3/6 QUERY OPTIMIZATION: Focus on generating short, entity-focused BM25 queries for steps 3 and 6.
    2. PATTERN LEVERAGE: Extend beneficial patterns (e.g., short entity queries) and avoid harmful ones (e.g., prose in queries).
    3. FAILURE REMOVAL: Eliminate patterns causing retrieval failures (e.g., non-verbatim queries in step 3/6).
    4. THIRD HOP BOOST: Prioritize strategies that improve the third hop (step 6) when coverage is low for the third document."""

    user = """EVOLUTIONARY MUTATION: Adaptive Code Evolution for HoVer Chains

    Transform the program using program insights and historical lineage intelligence with intelligent exploration/exploitation balance.

    ## INTELLIGENCE INPUTS

    **PROGRAM INSIGHTS**: [category][tag](severity) — concrete evidence about current program
    - Tags: beneficial (PRESERVE/EXTEND), harmful (REMOVE/AVOID), fragile (IMPROVE/ROBUSTIFY), rigid (MAKE ADAPTABLE), neutral (IGNORE)

    **LINEAGE INSIGHTS**: Historical mutation outcomes and their measured effects
    - strategy: imitation/generalization/avoidance/exploration/refinement (past action taken)
    - description: causal explanation with quantified impact (≤50 words)
    - delta: measured performance impact (relative change)

    **FAILURE ANALYSIS**: Wrong predictions with retrieval coverage — use to distinguish:
      - First hop failure (step 3 query) → fix step 3 query
      - Second hop failure (step 6 query) → fix step 6 query
      - Third hop failure (step 6 query) → fix step 6 query (most critical)

    ## EVOLUTIONARY ARCHETYPE SELECTION

    Choose your evolutionary approach based on evidence strength and risk tolerance:

    ### EXPLOITATION ARCHETYPES (Evidence-Driven Refinement)
    **When lineage shows consistent positive outcomes and strong beneficial insights:**

    1. **Step 3 Query Precision**
       → Fine-tune step 3 query generation, minimal risk changes, conservative improvements

    2. **Step 6 Query Precision**
       → Fine-tune step 6 query generation for third hop, critical for coverage

    3. **Harmful Pattern Removal**
       → Eliminate documented failure modes (e.g., prose in step 3/6 outputs)

    ### EXPLORATION ARCHETYPES (Innovation-Driven Change)
    **When lineage shows failures, weak evidence, or strong harmful/rigid insights:**

    4. **Third Hop Query Boost**
       → Novel techniques for step 6 query (e.g., leveraging step 5 evidence to find distantly-related documents)

    5. **Step 3 Query Diversification**
       → Generate alternative step 3 queries to avoid local minima

    6. **Cross-Hop Pattern Synthesis**
       → Combine evidence from multiple hops to form better queries

    ### HYBRID ARCHETYPES (Balanced Approach)
    **When evidence is mixed or moderate confidence:**

    7. **Guided Step 6 Innovation**
       → Preserve proven step 5 evidence consolidation while introducing targeted step 6 improvements

    8. **Conservative Step 3 Exploration**
       → Explore step 3 query variations within safe boundaries (e.g., entity extraction)

    ## OUTPUT FORMAT (JSON)

    {{
      \"archetype\": \"Selected archetype name\",
      \"justification\": \"2-3 sentences linking insights to changes.\",
      \"insights_used\": [\"insight1 text\", \"insight2 text\"],
      \"code\": \"complete Python program\"
    }}

    **CRITICAL**: The `code` field must contain ONLY valid Python code.

    {parent_blocks}"""

    return {"system": system, "user": user}
