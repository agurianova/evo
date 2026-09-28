def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert. Retrieve all evidence needed to verify the claim.",
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
            # Step 2: Generate second-hop query (branch A)
            {
                "number": 2,
                "title": "Generate second-hop query (branch A)",
                "step_type": "llm",
                "aim": "Identify one missing piece of evidence and generate a search query for the second hop (branch A).",
                "stage_action": (
                    "Based on the first-hop passages, determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query to find this evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: 'What was the outcome of the Battle of Hastings?'",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (branch B)
            {
                "number": 3,
                "title": "Generate second-hop query (branch B)",
                "step_type": "llm",
                "aim": "Identify a different missing piece of evidence and generate a search query for the second hop (branch B).",
                "stage_action": (
                    "Based on the first-hop passages, determine another piece of evidence (distinct from branch A) "
                    "that is needed to verify the claim. Write a concise search query to find this evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: 'Who was the king of England in 1066?'",
                "dependencies": [1],
            },
            # Step 4: Second-hop retrieval (branch A)
            {
                "number": 4,
                "title": "Retrieve second-hop passages (branch A)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (branch B)
            {
                "number": 5,
                "title": "Retrieve second-hop passages (branch B)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Review all retrieved passages (first-hop and both second-hop branches). Summarize the key evidence found. "
                    "Then, determine what specific evidence is still missing to confirm or refute the claim. "
                    "Write a concise search query to find the missing evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "1. What key facts have been established so far? 2. What specific information is still missing? 3. What is the most precise query to retrieve the missing evidence?",
                "example_reasoning": "Example: 'What was the population of London in 1800?'",
                "dependencies": [1, 4, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }