def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving relevant evidence from Wikipedia. Your goal is to find all supporting documents for the claim. At each step, focus on identifying missing evidence to fully verify the claim.",
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
                "aim": "Identify key missing evidence after first retrieval and generate precise second-hop query",
                "stage_action": (
                    "Analyze the first-hop passages to determine what specific fact or evidence is still missing to verify the claim. "
                    "Write a concise search query to find that missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to verify the claim?\n"
                    "Which entities or relationships need further evidence?"
                ),
                "example_reasoning": "<none>",
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
                "aim": "Identify remaining gaps using all evidence so far and generate precise third-hop query",
                "stage_action": (
                    "Integrate the first-hop and second-hop passages to identify the next missing piece of evidence. "
                    "Write a concise search query to find it.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence has been gathered so far?\n"
                    "What specific gap remains to fully verify the claim?"
                ),
                "example_reasoning": "<none>",
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
                "aim": "Identify final missing evidence and generate precise fourth-hop query",
                "stage_action": (
                    "Review all retrieved passages to determine the last piece of evidence needed. "
                    "Write a concise search query to find it.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the final missing fact to verify the claim?\n"
                    "What specific evidence would complete the verification?"
                ),
                "example_reasoning": "<none>",
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