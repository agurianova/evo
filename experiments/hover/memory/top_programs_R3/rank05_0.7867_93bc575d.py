def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your goal is to verify claims by retrieving all relevant supporting evidence from Wikipedia. Maximize retrieval coverage by generating precise search queries that capture missing evidence at each hop. Focus on specificity and avoid redundancy.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "First-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information after the first retrieval and generate a precise search query.",
                "stage_action": (
                    "Based on the first retrieval results, determine what specific evidence is still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key fact from the claim is not addressed by the first-hop passages? "
                    "What specific term or phrase would best capture the missing evidence in a search?"
                ),
                "example_reasoning": (
                    "The claim mentions 'X caused Y'. The first-hop passages discuss X but not its effect on Y. "
                    "The missing evidence is the causal link. Query: 'X effect on Y'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Second-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify residual gaps after two retrievals and generate a targeted search query.",
                "stage_action": (
                    "Integrate evidence from the first two retrievals. Determine what specific evidence is still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What does the combined evidence from the first two hops tell us? "
                    "What specific aspect of the claim remains unverified? "
                    "What precise search terms would address the remaining gap?"
                ),
                "example_reasoning": (
                    "The first two hops confirm X and Y but not the timing. The claim states 'X caused Y in 2020'. "
                    "The missing evidence is the year. Query: 'X Y 2020'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Third-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing piece of evidence and generate a highly specific search query.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine the exact piece of evidence still needed to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the one specific fact that would complete the verification? "
                    "What are the most precise search terms to find that fact?"
                ),
                "example_reasoning": (
                    "All evidence confirms the relationship but not the source. The claim requires a primary source. "
                    "Query: 'official report X Y 2020'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Fourth-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }