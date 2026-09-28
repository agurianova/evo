def entrypoint():
    return {
        "system_prompt": "You are an evidence specialist for claim verification. Your task is to guide the retrieval of evidence by generating precise search queries and synthesizing evidence with a focus on verification. For query generation steps: output ONLY the search query, nothing else. For synthesis steps: focus on identifying supporting/refuting evidence, temporal alignment, causal connections, and source credibility. Always perform explicit gap analysis after synthesis to identify missing evidence.",
        "steps": [
            # Step 1: First-hop retrieval (recall-focused)
            {
                "number": 1,
                "title": "First-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: First-hop synthesis with verification focus and prioritized gap analysis
            {
                "number": 2,
                "title": "First-hop synthesis and gap analysis",
                "step_type": "llm",
                "aim": "Integrate first-hop evidence and identify high-impact gaps for further retrieval.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to verifying the claim. "
                    "Focus on supporting/refuting evidence, temporal alignment, and causal connections. "
                    "Then, identify up to two specific gaps in the evidence that prevent full verification, "
                    "prioritizing gaps that would directly confirm/refute the claim or resolve critical inconsistencies."
                ),
                "reasoning_questions": (
                    "1. What specific facts from the passages directly support or refute the claim?\n"
                    "2. Are there temporal inconsistencies between the evidence and the claim?\n"
                    "3. What causal mechanisms are described that link the evidence to the claim?\n"
                    "4. What are the top two missing pieces of evidence needed to verify the claim, prioritized by their potential impact on verification (e.g., gaps that would directly confirm/refute the claim or resolve temporal/causal inconsistencies)? Be specific: e.g., 'evidence about [entity] in [time period]'."
                ),
                "example_reasoning": (
                    "Claim: 'Regular exercise improves cognitive function in older adults.'\n"
                    "Evidence: [Passage 1] A 2020 study showed improved memory in seniors who exercised. [Passage 2] Exercise increases blood flow to the brain.\n"
                    "Analysis:\n"
                    "  - Supporting: The study directly links exercise to memory improvement, and blood flow is a known factor in cognitive health.\n"
                    "  - Temporal: The study was conducted in 2020, which is recent and relevant.\n"
                    "  - Causal: Increased blood flow provides a mechanism for cognitive improvement.\n"
                    "Gaps:\n"
                    "  1. Long-term studies tracking cognitive decline over 10+ years in exercising vs. non-exercising older adults.\n"
                    "  2. Evidence of the effect in adults over 80 years old, as most studies focus on 60-75."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for first gap
            {
                "number": 3,
                "title": "Generate query for first gap",
                "step_type": "llm",
                "aim": "Generate a precise search query to find evidence for the first identified gap.",
                "stage_action": (
                    "Based on the first gap identified in the previous step, write a concise search query "
                    "that will retrieve evidence specifically addressing that gap. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Gap: 'Long-term studies tracking cognitive decline over 10+ years in exercising vs. non-exercising older adults.'\n"
                    "Query: 'long-term exercise cognitive decline older adults 10 years'"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate query for second gap (if exists)
            {
                "number": 4,
                "title": "Generate query for second gap",
                "step_type": "llm",
                "aim": "Generate a precise search query to find evidence for the second identified gap (if any).",
                "stage_action": (
                    "If a second gap was identified, write a concise search query for it. "
                    "If no second gap, output the exact string 'NO_QUERY' (all caps, no quotes). "
                    "Output ONLY the search query or 'NO_QUERY', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Gap: 'Evidence of the effect in adults over 80 years old, as most studies focus on 60-75.'\n"
                    "Query: 'exercise cognitive function adults over 80'\n\n"
                    "No second gap: 'NO_QUERY'"
                ),
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (branch A)
            {
                "number": 5,
                "title": "Second-hop retrieval (branch A)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Second-hop retrieval (branch B)
            {
                "number": 6,
                "title": "Second-hop retrieval (branch B)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 7: Synthesize all evidence with conditional branch handling
            {
                "number": 7,
                "title": "Second-hop synthesis and gap analysis",
                "step_type": "llm",
                "aim": "Integrate all evidence gathered so far and identify remaining gaps, ignoring invalid branches.",
                "stage_action": (
                    "Combine evidence from the first hop (step 1) and second hop branch A (step 5). "
                    "If the output of step 4 (the second gap query) is exactly the string 'NO_QUERY', skip branch B. "
                    "Otherwise, incorporate evidence from second hop branch B (step 6). "
                    "Extract verification-focused facts (supporting/refuting, temporal, causal). "
                    "Then, identify up to two specific gaps that remain for full verification."
                ),
                "reasoning_questions": (
                    "1. What new evidence from the second hop addresses the previous gaps?\n"
                    "2. What specific facts still support or refute the claim?\n"
                    "3. Are there any remaining temporal or causal inconsistencies?\n"
                    "4. What are the top two missing pieces of evidence needed now? (Be specific)"
                ),
                "example_reasoning": (
                    "Claim: 'Regular exercise improves cognitive function in older adults.'\n"
                    "First-hop evidence: [Passage 1] A 2020 study showed improved memory in seniors who exercised. [Passage 2] Exercise increases blood flow to the brain.\n"
                    "Second-hop evidence (branch A): [Passage 3] Long-term study (2010-2020) shows slower cognitive decline in exercisers.\n"
                    "Note: Step 4 output was 'NO_QUERY', so branch B was not retrieved.\n"
                    "Analysis:\n"
                    "  - Supporting: The long-term study provides strong evidence for the claim.\n"
                    "  - Temporal: All evidence is from the last decade, which is relevant.\n"
                    "  - Causal: The mechanism (blood flow) is supported by multiple studies.\n"
                    "Gaps:\n"
                    "  1. Evidence of the effect in diverse populations (e.g., different ethnicities, socioeconomic backgrounds)."
                ),
                "dependencies": [1, 4, 5, 6],
            },
            # Step 8: Generate combined query for remaining gaps
            {
                "number": 8,
                "title": "Generate combined query for remaining gaps",
                "step_type": "llm",
                "aim": "Generate a precise search query that combines the top two identified gaps to maximize evidence coverage in a single retrieval.",
                "stage_action": (
                    "Based on the gaps identified in the previous step, write a concise search query that will retrieve evidence "
                    "addressing both gaps. Combine the key terms from both gaps into a single query string. "
                    "If only one gap exists, use that gap. If no gaps, output the exact string 'NO_QUERY' (all caps, no quotes). "
                    "Output ONLY the search query or 'NO_QUERY', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Gaps:\n"
                    "  1. Long-term studies tracking cognitive decline over 10+ years in exercising vs. non-exercising older adults.\n"
                    "  2. Evidence of the effect in adults over 80 years old.\n"
                    "Query: 'long-term exercise cognitive decline older adults 10 years adults over 80'\n\n"
                    "Only one gap: 'exercise cognitive function diverse populations ethnicity'\n\n"
                    "No gaps: 'NO_QUERY'"
                ),
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval
            {
                "number": 9,
                "title": "Third-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }
