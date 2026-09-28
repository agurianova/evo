def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. Always follow these principles:\n- Be thorough: aim to find all relevant evidence to verify the claim.\n- When generating search queries, formulate the query to maximize the chance of retrieving relevant passages for the missing evidence.\n- When summarizing, include all facts directly relevant to the claim and integrate all evidence gathered so far.",
        "steps": [
            # Step 1: Initial broad retrieval (k=10)
            {
                "number": 1,
                "title": "Initial broad retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are directly relevant to verifying the claim. "
                    "Produce a comprehensive summary that includes all relevant facts found. Do not generate a search query."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (broad)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Determine if additional evidence is needed and generate a broad search query for the next hop.",
                "stage_action": (
                    "Identify the most critical missing piece of evidence and generate a broad but relevant search query to find it. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (k=10)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop and integrate with first-hop
            {
                "number": 5,
                "title": "Integrate second-hop evidence",
                "step_type": "llm",
                "aim": "Combine second-hop evidence with first-hop evidence into comprehensive evidence.",
                "stage_action": (
                    "Combine the previous evidence summary with the newly retrieved passages. "
                    "Extract all key facts relevant to the claim and produce a unified, comprehensive summary covering all evidence so far. "
                    "Do not generate a search query."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 2, 4],
            },
            # Step 6: Generate third-hop query (specific)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a specific search query for the next hop.",
                "stage_action": (
                    "Identify the specific missing piece of evidence and generate a precise search query targeting that gap. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval (k=10)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop and integrate
            {
                "number": 8,
                "title": "Integrate third-hop evidence",
                "step_type": "llm",
                "aim": "Combine third-hop evidence with previous comprehensive summary.",
                "stage_action": (
                    "Combine the previous evidence summary with the newly retrieved passages. "
                    "Extract all key facts relevant to the claim and produce an updated unified comprehensive summary. "
                    "Do not generate a search query."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4, 5, 7],
            },
            # Step 9: Generate fourth-hop query (specific)
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a specific search query for the next hop.",
                "stage_action": (
                    "Identify the specific missing piece of evidence and generate a precise search query targeting that gap. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval (k=10)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }