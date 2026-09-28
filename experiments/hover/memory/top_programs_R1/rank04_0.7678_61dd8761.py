def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your task is to verify claims by retrieving relevant evidence. Always focus on identifying missing information and generating precise queries to fill gaps.",
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
            # Step 2: Generate first query for second hop
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify a critical missing piece of evidence and generate a focused search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence, determine one specific fact that is missing and needed to verify the claim. "
                    "Write a concise search query to find that fact. Output ONLY the query, no additional text."
                ),
                "reasoning_questions": "What is the most critical missing fact? How can we phrase the query to be specific and retrieve relevant passages?",
                "example_reasoning": "Example: Claim needs birth year. Query: 'Albert Einstein birth year'",
                "dependencies": [1],
            },
            # Step 3: Generate second query for second hop
            {
                "number": 3,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different critical missing piece of evidence and generate a focused search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence, determine a second specific fact that is missing (distinct from the first query) and needed to verify the claim. "
                    "Write a concise search query to find that fact. Output ONLY the query, no additional text."
                ),
                "reasoning_questions": "What is another critical missing fact (distinct from the first)? How can we phrase the query to avoid overlap with the first query?",
                "example_reasoning": "Example: Claim needs birth place. Query: 'Albert Einstein birth place'",
                "dependencies": [1],
            },
            # Step 4: Second-hop retrieval (query1)
            {
                "number": 4,
                "title": "Retrieve second-hop passages (query1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (query2)
            {
                "number": 5,
                "title": "Retrieve second-hop passages (query2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Synthesize evidence and check for gaps
            {
                "number": 6,
                "title": "Synthesize evidence and identify gaps",
                "step_type": "llm",
                "aim": "Combine all evidence and determine if the claim can be verified or if more evidence is needed for the third hop.",
                "stage_action": (
                    "Review the first-hop evidence and both sets of second-hop evidence. List all verified facts and identify any remaining gaps. "
                    "If there is a critical gap, generate a search query for the third hop. If no gaps remain, output 'NO_QUERY_NEEDED'. "
                    "Output ONLY the query or 'NO_QUERY_NEEDED', no additional text."
                ),
                "reasoning_questions": "What facts have been verified? What is the most critical remaining gap (if any)? How to phrase the query for the gap?",
                "example_reasoning": "Example: Verified: birth year. Missing: birth place. Query: 'Albert Einstein birth place'",
                "dependencies": [1, 4, 5],
            },
            # Step 7: Third-hop retrieval (if needed)
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