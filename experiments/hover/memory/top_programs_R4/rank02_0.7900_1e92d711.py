def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims by retrieving and analyzing evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim.",
        "steps": [
            # Step 1: First-hop retrieval on the claim
            {
                "number": 1,
                "title": "Initial evidence retrieval",
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
                "aim": "Identify the first missing piece of evidence needed to verify the claim and generate a search query for it.",
                "stage_action": (
                    "Analyze the retrieved passages to determine what specific fact is missing to verify the claim. "
                    "Write a concise search query to find this evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the claim? "
                    "What evidence have we found so far? "
                    "What specific fact is still missing to verify the claim?"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Second-hop evidence retrieval",
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
                "aim": "Identify the next missing piece of evidence given all evidence gathered so far and generate a search query for it.",
                "stage_action": (
                    "Integrate evidence from all retrieved passages to determine what additional specific fact is missing. "
                    "Write a concise search query to find this evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence have we gathered from the first and second hops? "
                    "What specific fact is still missing to verify the claim?"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Third-hop evidence retrieval",
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
                "aim": "Identify the final missing piece of evidence (if any) and generate a search query for it.",
                "stage_action": (
                    "Synthesize all evidence gathered so far to determine if there is any remaining gap. "
                    "If so, write a concise search query to find the final missing evidence. "
                    "If no gap exists, output a query that will retrieve general context (e.g., the claim itself). "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence have we gathered from all three hops? "
                    "Is there any specific fact still missing to verify the claim? "
                    "If yes, what is it?"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Fourth-hop evidence retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }