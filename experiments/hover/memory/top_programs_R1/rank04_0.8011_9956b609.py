def entrypoint():
    return {
        "system_prompt": "You are a fact-checker. At each hop, identify the next verifiable fact needed to confirm or refute the claim. Always prioritize identifying missing evidence for verification.",
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
                "aim": "Identify the most critical missing piece of evidence and generate a search query for it.",
                "stage_action": (
                    "Based on the first-hop evidence, determine the single most important fact missing to verify the claim. "
                    "Write a concise search query to find this fact. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing? "
                    "How can this fact be phrased as a concise search query?"
                ),
                "example_reasoning": (
                    "Example: Claim is 'John Doe was born in 1980'. Missing fact: birth year. Query: 'John Doe birth year'"
                ),
                "dependencies": [1],
            },
            # Step 3: First second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second second-hop query (diverse from first)
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Generate a distinct search query for complementary missing evidence.",
                "stage_action": (
                    "Based on the first-hop evidence and the first second-hop evidence, generate a search query for a different missing fact. "
                    "The query should seek information not covered by the previous query. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Given the first-hop evidence and the first second-hop evidence, what other specific fact is still missing? "
                    "How can this fact be phrased as a concise search query that differs from the previous one?"
                ),
                "example_reasoning": (
                    "Example: Previous query was 'John Doe birth year' and results showed birth year is 1980. "
                    "Now, missing fact: birth place. Query: 'John Doe birth place'"
                ),
                "dependencies": [1, 2, 3],
            },
            # Step 5: Second second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve second second-hop passages",
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
                "aim": "Identify the final missing piece of evidence and generate a distinct search query for it.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what single piece of evidence is still missing to verify the claim. "
                    "Write a concise search query to find this fact, ensuring it is distinct from the previous two queries. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is still missing that hasn't been addressed by the previous queries? "
                    "How can this fact be phrased as a concise search query distinct from the previous two queries?"
                ),
                "example_reasoning": (
                    "Example: Previous queries were 'John Doe birth year' and 'John Doe birth place'. "
                    "Now, missing fact: birth date (day and month). Query: 'John Doe birth date'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }