def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Always focus on identifying gaps in the current evidence and generating precise search queries to fill those gaps. Provide only the necessary output as instructed.",
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the missing evidence needed to verify the claim and generate a precise search query to retrieve it.",
                "stage_action": (
                    "Based on the claim and all retrieved evidence so far, determine what specific information is still missing to verify the claim. "
                    "Formulate a concise search query that targets only the missing information.\n"
                    "Output exactly one line of text: the search query. Do not include any other text."
                ),
                "reasoning_questions": "What specific fact is still missing? How can we phrase a query to get that fact?",
                "example_reasoning": (
                    "Example: Claim: 'The first moon landing was in 1969.'\n"
                    "Evidence so far: Passages mention Apollo 11 mission but not the exact date.\n"
                    "Gap: The exact date of the moon landing.\n"
                    "Query: 'Apollo 11 moon landing date'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
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
                "aim": "Identify the missing evidence needed to verify the claim and generate a precise search query to retrieve it.",
                "stage_action": (
                    "Based on the claim and all retrieved evidence so far, determine what specific information is still missing to verify the claim. "
                    "Formulate a concise search query that targets only the missing information.\n"
                    "Output exactly one line of text: the search query. Do not include any other text."
                ),
                "reasoning_questions": "What specific fact is still missing? How can we phrase a query to get that fact?",
                "example_reasoning": (
                    "Example: Claim: 'The first moon landing was in 1969.'\n"
                    "Evidence so far: Passages mention Apollo 11 mission but not the exact date.\n"
                    "Gap: The exact date of the moon landing.\n"
                    "Query: 'Apollo 11 moon landing date'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
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
                "aim": "Identify the missing evidence needed to verify the claim and generate a precise search query to retrieve it.",
                "stage_action": (
                    "Based on the claim and all retrieved evidence so far, determine what specific information is still missing to verify the claim. "
                    "Formulate a concise search query that targets only the missing information.\n"
                    "Output exactly one line of text: the search query. Do not include any other text."
                ),
                "reasoning_questions": "What specific fact is still missing? How can we phrase a query to get that fact?",
                "example_reasoning": (
                    "Example: Claim: 'The first moon landing was in 1969.'\n"
                    "Evidence so far: Passages mention Apollo 11 mission but not the exact date.\n"
                    "Gap: The exact date of the moon landing.\n"
                    "Query: 'Apollo 11 moon landing date'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }