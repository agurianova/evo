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
            # Step 2: Generate first second-hop query
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify one missing piece of evidence and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the retrieved passages, determine what additional evidence is needed to "
                    "verify the claim. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: 'What was the population of Tokyo in 2020?'",
                "dependencies": [1],
            },
            # Step 3: Generate second second-hop query
            {
                "number": 3,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different missing piece of evidence (complementary to the first) and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the retrieved passages, determine a different piece of additional evidence "
                    "needed to verify the claim (complementary to the first query). Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: 'What was the GDP of Japan in 2020?'",
                "dependencies": [1],
            },
            # Step 4: First second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve with first second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Second second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve with second second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Combine evidence and generate third-hop query
            {
                "number": 6,
                "title": "Combine evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Integrate all evidence gathered so far and identify the final missing piece to generate a third-hop query.",
                "stage_action": (
                    "Review the first-hop passages (step 1), the first second-hop passages (step 4), "
                    "and the second second-hop passages (step 5). Identify what critical evidence is "
                    "still missing to verify the claim. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What are the key entities in the claim? What evidence have we gathered so far? "
                    "What is the most critical missing piece of evidence?"
                ),
                "example_reasoning": "Example: 'When did World War II end?'",
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