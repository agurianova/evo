def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to verify claims by retrieving supporting evidence from Wikipedia. Always refer to the original claim in the Data section for context. When generating search queries, ensure they are focused on finding evidence for the original claim. Your reasoning should be step-by-step and address the specific questions provided.\n\nIMPORTANT: In steps that generate search queries, output ONLY the search query without any other text. ANY extra text (including quotes, explanations, or newlines) will break the system.",
        "steps": [
            # Step 1: First-hop retrieval with higher recall
            {
                "number": 1,
                "title": "Retrieve initial passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence with ranked gaps
            {
                "number": 2,
                "title": "Summarize evidence and rank gaps",
                "step_type": "llm",
                "aim": "Extract key facts and identify up to 3 critical evidence gaps ranked by importance.",
                "stage_action": (
                    "Read all retrieved passages and identify facts relevant to verifying the claim. "
                    "Summarize evidence in 2-3 bullet points. Then list up to 3 remaining evidence gaps as numbered bullet points (1=most critical, 3=least critical) under 'GAPS:'. "
                    "Be specific about missing information and prioritize gaps that directly impact claim verification."
                ),
                "reasoning_questions": (
                    "1. What specific facts directly support or refute the claim?\n"
                    "2. Are there any contradictions in the evidence?\n"
                    "3. What are the top 3 critical missing pieces (ranked 1-3)?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Passage [1]: 'The Eiffel Tower was built as the entrance arch for the 1889 World's Fair... intended to be dismantled after 20 years.'\n"
                    "Evidence summary:\n"
                    "- Built for 1889 World's Fair\n"
                    "- Intended dismantling after 20 years\n"
                    "GAPS:\n"
                    "1. Why wasn't it dismantled? (most critical)\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Who made the final decision?"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for top gap
            {
                "number": 3,
                "title": "Generate query for #1 gap",
                "step_type": "llm",
                "aim": "Create precise query for most critical gap.",
                "stage_action": (
                    "Based on the TOP-RANKED gap (gap #1) from step2, generate ONE search query. "
                    "Focus exclusively on the most critical missing information. "
                    "Output ONLY the query string. ANY extra text will break the system."
                ),
                "reasoning_questions": (
                    "1. What is the exact missing information in gap #1?\n"
                    "2. How to phrase the most precise query for this?\n"
                    "3. What keywords will yield the highest precision results?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "GAPS from step2:\n"
                    "1. Why wasn't it dismantled?\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Who made the final decision?\n"
                    "Why was the Eiffel Tower not dismantled after 20 years?"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate query for second gap
            {
                "number": 4,
                "title": "Generate query for #2 gap",
                "step_type": "llm",
                "aim": "Create precise query for second critical gap.",
                "stage_action": (
                    "Based on gap #2 from step2 (SECOND most critical), generate ONE search query. "
                    "Ensure it's distinct from step3's query. "
                    "Output ONLY the query string. ANY extra text will break the system."
                ),
                "reasoning_questions": (
                    "1. What is the exact missing information in gap #2?\n"
                    "2. How to phrase a query different from step3's?\n"
                    "3. What unique keywords should this query use?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "GAPS from step2:\n"
                    "1. Why wasn't it dismantled?\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Who made the final decision?\n"
                    "When was Eiffel Tower declared permanent structure?"
                ),
                "dependencies": [2],
            },
            # Step 5: Generate query for third gap
            {
                "number": 5,
                "title": "Generate query for #3 gap",
                "step_type": "llm",
                "aim": "Create precise query for third critical gap.",
                "stage_action": (
                    "Based on gap #3 from step2 (THIRD most critical), generate ONE search query. "
                    "Ensure it's distinct from steps 3-4 queries. "
                    "Output ONLY the query string. ANY extra text will break the system."
                ),
                "reasoning_questions": (
                    "1. What is the exact missing information in gap #3?\n"
                    "2. How to phrase a query different from previous branches?\n"
                    "3. What unique keywords should this query use?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "GAPS from step2:\n"
                    "1. Why wasn't it dismantled?\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Who made the final decision?\n"
                    "Who decided to keep the Eiffel Tower permanently?"
                ),
                "dependencies": [2],
            },
            # Step 6: Retrieve for top gap
            {
                "number": 6,
                "title": "Retrieve passages for #1 gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 7: Retrieve for second gap
            {
                "number": 7,
                "title": "Retrieve passages for #2 gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 8: Retrieve for third gap
            {
                "number": 8,
                "title": "Retrieve passages for #3 gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 9: Merge evidence and generate next query
            {
                "number": 9,
                "title": "Merge evidence and generate next query",
                "step_type": "llm",
                "aim": "Integrate all evidence and generate query for top remaining gap or signal completion.",
                "stage_action": (
                    "Combine evidence from step2 summary and steps6-8 retrievals. "
                    "If ALL original evidence gaps from step2 are resolved, output exactly 'NO_GAPS'. "
                    "Otherwise, identify the SINGLE most critical remaining gap and generate a search query for it. "
                    "Output ONLY the query string or 'NO_GAPS'. ANY extra text will break the system."
                ),
                "reasoning_questions": (
                    "1. Which step2 gaps were resolved by steps6-8?\n"
                    "2. What is the most critical UNRESOLVED gap?\n"
                    "3. How to phrase the most precise query for this gap?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Step2 summary: Built for 1889 Fair, intended dismantling after 20 years. GAPS: 1. Why not dismantled? 2. When permanent? 3. Who decided?\n"
                    "Branch #1: Saved by radio communications during WWI\n"
                    "Branch #2: Permanent status confirmed in 1910\n"
                    "Branch #3: Decision made by City of Paris\n"
                    "Combined evidence resolves all gaps -> NO_GAPS\n\n"
                    "--- ALTERNATE EXAMPLE ---\n\n"
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Step2 summary: ... GAPS: 1. Why not dismantled? 2. When permanent? 3. Who decided?\n"
                    "Branch #1: Saved by radio communications during WWI\n"
                    "Branch #2: [No relevant info]\n"
                    "Branch #3: [No relevant info]\n"
                    "Remaining critical gap: When permanent status confirmed?\n"
                    "When was Eiffel Tower declared permanent structure?"
                ),
                "dependencies": [2, 6, 7, 8],
            },
            # Step 10: Final retrieval
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
