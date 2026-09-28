def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to verify claims by retrieving supporting evidence from Wikipedia. Always refer to the original claim in the Data section for context. When generating search queries, ensure they are focused on finding evidence for the original claim. Your reasoning should be step-by-step and address the specific questions provided.\n\nIMPORTANT: In steps that generate search queries, output ONLY the search query without any other text. ANY extra text (including quotes, explanations, or newlines) will break the system.",
        "steps": [
            # Step 1: First-hop retrieval with deep recall
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
            # Step 2: Summarize first-hop evidence with ranked gaps (now 4 gaps)
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts and identify top 4 structured gaps (ranked by criticality) from retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts relevant to verifying the claim. "
                    "Summarize evidence in 2-3 bullet points. Then list the top 4 remaining evidence gaps as bullet points under 'GAPS (ranked 1-4):'. "
                    "Be specific about what information is still needed and rank gaps by criticality (1 = most critical) with the following criteria: gaps that directly support or refute the claim are most critical."
                ),
                "reasoning_questions": (
                    "1. What specific facts directly support or refute the claim?\n"
                    "2. Are there any contradictions in the evidence?\n"
                    "3. What are the top 4 critical missing information items (ranked 1-4)?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Passage [1]: 'The Eiffel Tower was built as the entrance arch for the 1889 World's Fair... intended to be dismantled after 20 years.'\n"
                    "Evidence summary:\n"
                    "- Built for 1889 World's Fair\n"
                    "- Intended dismantling after 20 years\n"
                    "GAPS (ranked 1-4):\n"
                    "1. Why wasn't it dismantled? (most critical)\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Official documentation source?\n"
                    "4. What was the role of World War I in saving the tower?"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for gap #1 (enhanced robustness)
            {
                "number": 3,
                "title": "Generate query for gap #1",
                "step_type": "llm",
                "aim": "Create focused query for the most critical gap (ranked #1 from step2).",
                "stage_action": (
                    "Based on the top gap (ranked #1) from step2, generate ONE search query targeting this specific gap. "
                    "Output ONLY the query string. Do not include any other text, not even quotes, explanations, or newlines. The output must be exactly the query string."
                ),
                "reasoning_questions": (
                    "1. What is the exact information need for gap #1?\n"
                    "2. How to phrase the most precise query for this gap?\n"
                    "3. What keywords will yield relevant results?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "GAPS from step2:\n"
                    "1. Why wasn't it dismantled?\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Official documentation source?\n"
                    "4. What was the role of World War I in saving the tower?\n"
                    "Why was the Eiffel Tower not dismantled after 20 years?"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate query for gap #2 (enhanced robustness)
            {
                "number": 4,
                "title": "Generate query for gap #2",
                "step_type": "llm",
                "aim": "Create focused query for the second critical gap (ranked #2 from step2).",
                "stage_action": (
                    "Based on the second gap (ranked #2) from step2, generate ONE search query targeting this specific gap. "
                    "Output ONLY the query string. Do not include any other text, not even quotes, explanations, or newlines. The output must be exactly the query string."
                ),
                "reasoning_questions": (
                    "1. What is the exact information need for gap #2?\n"
                    "2. How to phrase a query distinct from gap #1?\n"
                    "3. What unique keywords should this query use?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "GAPS from step2:\n"
                    "1. Why wasn't it dismantled?\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Official documentation source?\n"
                    "4. What was the role of World War I in saving the tower?\n"
                    "When was Eiffel Tower declared permanent structure?"
                ),
                "dependencies": [2],
            },
            # Step 5: Generate query for gap #3 (enhanced robustness)
            {
                "number": 5,
                "title": "Generate query for gap #3",
                "step_type": "llm",
                "aim": "Create focused query for the third critical gap (ranked #3 from step2).",
                "stage_action": (
                    "Based on the third gap (ranked #3) from step2, generate ONE search query targeting this specific gap. "
                    "Output ONLY the query string. Do not include any other text, not even quotes, explanations, or newlines. The output must be exactly the query string."
                ),
                "reasoning_questions": (
                    "1. What is the exact information need for gap #3?\n"
                    "2. How to phrase a query distinct from gaps #1 and #2?\n"
                    "3. What unique keywords should this query use?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "GAPS from step2:\n"
                    "1. Why wasn't it dismantled?\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Official documentation source?\n"
                    "4. What was the role of World War I in saving the tower?\n"
                    "Official document confirming Eiffel Tower permanent status"
                ),
                "dependencies": [2],
            },
            # Step 6: Generate query for gap #4 (new branch)
            {
                "number": 6,
                "title": "Generate query for gap #4",
                "step_type": "llm",
                "aim": "Create focused query for the fourth critical gap (ranked #4 from step2).",
                "stage_action": (
                    "Based on the fourth gap (ranked #4) from step2, generate ONE search query targeting this specific gap. "
                    "Output ONLY the query string. Do not include any other text, not even quotes, explanations, or newlines. The output must be exactly the query string."
                ),
                "reasoning_questions": (
                    "1. What is the exact information need for gap #4?\n"
                    "2. How to phrase a query distinct from gaps #1-3?\n"
                    "3. What unique keywords should this query use?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "GAPS from step2:\n"
                    "1. Why wasn't it dismantled?\n"
                    "2. When was permanent status confirmed?\n"
                    "3. Official documentation source?\n"
                    "4. What was the role of World War I in saving the tower?\n"
                    "Role of World War I in Eiffel Tower preservation"
                ),
                "dependencies": [2],
            },
            # Step 7: Retrieve Branch A (gap #1)
            {
                "number": 7,
                "title": "Retrieve Branch A passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 8: Retrieve Branch B (gap #2)
            {
                "number": 8,
                "title": "Retrieve Branch B passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 9: Retrieve Branch C (gap #3)
            {
                "number": 9,
                "title": "Retrieve Branch C passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 10: Retrieve Branch D (gap #4)
            {
                "number": 10,
                "title": "Retrieve Branch D passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }
