def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to verify claims by retrieving supporting evidence from Wikipedia. Always refer to the original claim in the Data section for context. When generating search queries, ensure they are focused on finding evidence for the original claim. Your reasoning should be step-by-step and address the specific questions provided. In steps that generate search queries, output ONLY the search query without any other text. Any extra text will break the system.",
        "steps": [
            # Step 1: First-hop retrieval with precision optimization
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence with structured gaps
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts and identify structured gaps for parallel inquiry",
                "stage_action": (
                    "Read all retrieved passages and identify facts relevant to verifying the claim. "
                    "Summarize key evidence in 2-3 sentences. Then, list remaining evidence gaps in bullet points "
                    "(e.g., '- Gap 1: ...'). Do not output 'NO_GAPS' as we will perform additional hops."
                ),
                "reasoning_questions": (
                    "1. What specific facts directly support/refute the claim?\n"
                    "2. What are the 1-2 most critical missing pieces of evidence?\n"
                    "3. How can these gaps be phrased as independent search queries?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Passage [1]: 'Built for 1889 World's Fair, intended dismantling after 20 years.'\n"
                    "Summary: The tower was constructed for the 1889 World's Fair with a planned 20-year lifespan.\n"
                    "Gaps:\n"
                    "- Why wasn't it dismantled after 20 years?\n"
                    "- When was the permanent status decision made?"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate first second-hop query (Branch A) with strict output
            {
                "number": 3,
                "title": "Generate Branch A query",
                "step_type": "llm",
                "aim": "Create precise query for first evidence gap",
                "stage_action": (
                    "Based on the first-hop evidence summary and gap list, select the most critical gap. "
                    "Formulate a concise search query targeting ONLY that gap.\n"
                    "Output ONLY the search query. Do not include any other text, not even quotes or explanations. "
                    "ANY extra text will break the system."
                ),
                "reasoning_questions": (
                    "1. Which gap has the clearest path to verification?\n"
                    "2. What keywords will yield the most relevant results for this gap?\n"
                    "3. How can we avoid overlapping with potential Branch B queries?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower was temporary'\n"
                    "Gaps: - Why not dismantled after 20 years?\n"
                    "          - When was permanent decision made?\n"
                    "Why was the Eiffel Tower not dismantled after 20 years?"
                ),
                "dependencies": [2],
            },
            # Step 4: Branch A retrieval
            {
                "number": 4,
                "title": "Retrieve Branch A passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize Branch A with structured gaps
            {
                "number": 5,
                "title": "Summarize Branch A evidence",
                "step_type": "llm",
                "aim": "Extract Branch A evidence and identify residual gaps",
                "stage_action": (
                    "Integrate Branch A retrieved passages with first-hop evidence. "
                    "Summarize key findings in 2-3 sentences. Then, list remaining evidence gaps "
                    "in bullet points (e.g., '- Gap 1: ...')."
                ),
                "reasoning_questions": (
                    "1. What new evidence does Branch A provide?\n"
                    "2. Which original gaps were filled?\n"
                    "3. What gaps remain after Branch A?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower was temporary'\n"
                    "First-hop: Planned 20-year lifespan.\n"
                    "Branch A: Saved by radio communications during WWI.\n"
                    "Summary: Military radio use during WWI prevented dismantling.\n"
                    "Gaps:\n"
                    "- When exactly was permanent status granted?\n"
                    "- What was the official reason for preservation?"
                ),
                "dependencies": [4],
            },
            # Step 6: Generate second second-hop query (Branch B) with strict output
            {
                "number": 6,
                "title": "Generate Branch B query",
                "step_type": "llm",
                "aim": "Create query for independent second gap",
                "stage_action": (
                    "Based on first-hop summary and Branch A results, identify a DIFFERENT critical gap. "
                    "Formulate a concise search query targeting ONLY that gap.\n"
                    "Output ONLY the search query. Do not include any other text. "
                    "ANY extra text will break the system."
                ),
                "reasoning_questions": (
                    "1. What gap remains UNADDRESSED by Branch A?\n"
                    "2. How can we phrase a query that avoids Branch A's evidence path?\n"
                    "3. What keywords are unique to this second line of inquiry?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower was temporary'\n"
                    "First-hop gaps: Why not dismantled? When permanent decision?\n"
                    "Branch A filled: 'Why not dismantled' (radio use).\n"
                    "Remaining gap: When was permanent status decision made?\n"
                    "When was the Eiffel Tower declared a permanent structure?"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Branch B retrieval
            {
                "number": 7,
                "title": "Retrieve Branch B passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize Branch B with structured gaps
            {
                "number": 8,
                "title": "Summarize Branch B evidence",
                "step_type": "llm",
                "aim": "Extract Branch B evidence and identify final gaps",
                "stage_action": (
                    "Integrate Branch B retrieved passages with all previous evidence. "
                    "Summarize key findings in 2-3 sentences. Then, list remaining evidence gaps "
                    "in bullet points (e.g., '- Gap 1: ...')."
                ),
                "reasoning_questions": (
                    "1. What new evidence does Branch B provide?\n"
                    "2. How does it complement Branch A?\n"
                    "3. Are there ANY remaining gaps for full verification?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower was temporary'\n"
                    "Previous evidence: Saved by WWI radio use.\n"
                    "Branch B: Decision formalized in 1909 due to military value.\n"
                    "Summary: Permanent status was granted in 1909 when military value was recognized.\n"
                    "Gaps:\n"
                    "- None - all claim elements verified."
                ),
                "dependencies": [7],
            },
            # Step 9: Final gap check with multi-gap handling
            {
                "number": 9,
                "title": "Verify evidence completeness",
                "step_type": "llm",
                "aim": "Determine if all evidence gaps are filled",
                "stage_action": (
                    "Synthesize ALL evidence (first-hop, Branch A, Branch B). "
                    "If EVERY aspect of the claim is supported by evidence, output EXACTLY 'NO_GAPS'. "
                    "Otherwise, output a SINGLE search query that covers ALL remaining gaps (e.g., by combining gap phrases with 'OR').\n"
                    "Output ONLY 'NO_GAPS' or the search query. Do not include any other text. "
                    "ANY extra text will break the system."
                ),
                "reasoning_questions": (
                    "1. Does evidence cover ALL claim components?\n"
                    "2. What specific elements remain unsupported?\n"
                    "3. How can we formulate a single query that covers all remaining gaps (e.g., by combining gap phrases with 'OR')?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "First-hop: Built for 1889 World's Fair, intended dismantling after 20 years.\n"
                    "Branch A: Saved due to radio communications use in WWI.\n"
                    "Branch B: Permanent status granted in 1909.\n"
                    "After synthesizing all evidence, the claim is partially verified: we know it was temporary and why it wasn't dismantled (military use), and when it became permanent (1909). However, the official reason for preservation and the exact date of the decision are missing.\n"
                    "Official reason for Eiffel Tower preservation OR date of permanent status decision"
                ),
                "dependencies": [2, 5, 8],
            },
            # Step 10: Final retrieval (skipped when NO_GAPS)
            {
                "number": 10,
                "title": "Retrieve final evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }
