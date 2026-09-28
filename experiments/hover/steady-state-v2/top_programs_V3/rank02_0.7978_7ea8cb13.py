def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving supporting evidence from Wikipedia. When generating search queries, output ONLY the query string with no additional text. When summarizing evidence, be concise and focus on facts relevant to the claim.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query for aspect A
            {
                "number": 3,
                "title": "Generate second-hop query for aspect A",
                "step_type": "llm",
                "aim": "Identify one key missing piece of evidence from the first-hop summary and generate a focused search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, determine one specific aspect that requires additional evidence "
                    "to verify the claim. Write a concise search query to find evidence for this aspect.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "First-hop summary indicates that the claim involves 'climate change impact on polar bears'. One missing piece is the current population trend. Query: 'polar bear population trend 2023'",
                "dependencies": [2],
            },
            # Step 4: Generate second-hop query for aspect B
            {
                "number": 4,
                "title": "Generate second-hop query for aspect B",
                "step_type": "llm",
                "aim": "Identify a different key missing piece of evidence from the first-hop summary and generate an alternative search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, determine a different specific aspect that requires additional evidence "
                    "(distinct from the one in step 3). Write a concise search query to find evidence for this aspect.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "First-hop summary indicates that the claim involves 'climate change impact on polar bears'. Another missing piece is the effect of sea ice loss. Query: 'sea ice loss effect on polar bear survival'",
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval for aspect A (deeper)
            {
                "number": 5,
                "title": "Retrieve second-hop passages for aspect A",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},  # step3 output
                },
                "dependencies": [3],
            },
            # Step 6: Second-hop retrieval for aspect B (deeper)
            {
                "number": 6,
                "title": "Retrieve second-hop passages for aspect B",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},  # step4 output
                },
                "dependencies": [4],
            },
            # Step 7: Combine evidence from all hops so far
            {
                "number": 7,
                "title": "Combine evidence from all hops so far",
                "step_type": "llm",
                "aim": "Integrate the first-hop evidence summary with the second-hop retrieved passages to form a comprehensive evidence base.",
                "stage_action": (
                    "Review the first-hop summary and both sets of second-hop retrieved passages. "
                    "Extract all relevant facts and synthesize them into a single, concise evidence summary "
                    "covering all aspects found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5, 6],
            },
            # Step 8: Generate third-hop query
            {
                "number": 8,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the final piece of evidence needed to fully verify the claim based on the combined evidence summary.",
                "stage_action": (
                    "Based on the comprehensive evidence summary, determine what additional evidence is still missing "
                    "to fully verify the claim. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Combined summary covers population trend and sea ice loss, but lacks information on conservation efforts. Query: 'polar bear conservation efforts effectiveness'",
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval (deeper)
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},  # step8 output
                },
                "dependencies": [8],
            },
        ],
    }