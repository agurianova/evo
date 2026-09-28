def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Always prioritize identifying missing evidence and gaps in the current knowledge. Focus on generating precise search queries to retrieve the necessary evidence for verification.",
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
            # Step 2: Generate first second-hop query (gap-focused)
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify a critical missing fact from the first-hop evidence and generate a search query for it.",
                "stage_action": (
                    "Read the first-hop retrieved passages. Identify one critical missing fact needed to verify the claim. "
                    "Write a concise search query to find that missing fact.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What fact is missing from the first-hop evidence? How can we phrase the query concisely?",
                "example_reasoning": "Example: Claim states 'John was born in 1990'. First-hop passages mention John's career but not birth year. Missing fact: birth year. Query: 'John birth year'",
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
            # Step 4: Generate second second-hop query (diverse gap)
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify an additional critical missing fact given the new evidence and generate a distinct search query.",
                "stage_action": (
                    "Read the first-hop retrieved passages and the first second-hop retrieved passages. "
                    "Identify one critical missing fact that is distinct from the previous query's intent. "
                    "Write a concise search query to find that missing fact.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "Given the additional evidence, what other critical gap remains? How to phrase a new query that is distinct from the first?",
                "example_reasoning": "Example: First query found birth year. Now we need birth place. Query: 'John birth place'",
                "dependencies": [1, 3],
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
                "aim": "Identify the final critical missing fact and generate a search query for it.",
                "stage_action": (
                    "Read all retrieved passages so far (first-hop and both second-hop). "
                    "Identify the final critical missing fact needed to verify the claim. "
                    "Write a concise search query to find that missing fact.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What final piece of evidence is missing? How to phrase the query concisely?",
                "example_reasoning": "Example: Claim needs birth certificate location. Query: 'John birth certificate location'",
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