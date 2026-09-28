def entrypoint():
    return {
        "system_prompt": "You are a fact-checker. Always prioritize identifying missing evidence for verification.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve initial evidence",
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
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information from initial evidence",
                "stage_action": (
                    "Based on the retrieved passages, determine the single most important fact missing "
                    "to verify the claim. Write a concise search query to find that fact. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact would most directly confirm or refute the claim? "
                    "How can this fact be phrased as a minimal search query?"
                ),
                "example_reasoning": (
                    "Example: Claim states 'John Doe was born in 1980' but evidence lacks birth year. "
                    "Query: 'John Doe birth year'"
                ),
                "dependencies": [1],
            },
            # Step 3: First second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve primary second-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate alternative second-hop query
            {
                "number": 4,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify a different critical missing information from initial evidence",
                "stage_action": (
                    "Based on the same initial evidence, determine a different key fact missing "
                    "to verify the claim. Write a concise search query for that fact. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What other specific fact would help verify the claim? "
                    "How can this fact be phrased as a minimal search query?"
                ),
                "example_reasoning": (
                    "Example: Claim states 'John Doe was born in 1980' but evidence lacks birthplace. "
                    "Query: 'John Doe birthplace'"
                ),
                "dependencies": [1],
            },
            # Step 5: Alternative second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve alternative second-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps using all evidence gathered",
                "stage_action": (
                    "Based on all retrieved evidence, determine the single most important fact still missing "
                    "to fully verify the claim. Write a concise search query to find that fact. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What critical fact remains unverified? "
                    "How can this fact be phrased as a minimal search query?"
                ),
                "example_reasoning": (
                    "Example: Claim needs death year for verification. "
                    "Query: 'John Doe death year'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }