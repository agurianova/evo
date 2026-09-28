def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert. Your goal is to maximize the retrieval of relevant evidence by generating precise search queries at each hop. Always consider the entire evidence gathered so far to identify the most critical missing information.",
        "steps": [
            # Step 1: Initial retrieval
            {
                "number": 1,
                "title": "Retrieve initial passages",
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
                "aim": "Identify the first missing piece of evidence after reviewing the initial passages.",
                "stage_action": (
                    "Based on the initial retrieved passages, determine what specific fact is still missing to verify the claim. "
                    "Write a concise search query to find that missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key fact mentioned in the claim is not supported by the initial passages? "
                    "What specific term or phrase would help find evidence for that fact?"
                ),
                "example_reasoning": (
                    "The claim states 'X is caused by Y'. The initial passages mention X but not Y. "
                    "I need to search for 'Y causes X'."
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
                "aim": "Identify the next missing piece of evidence after reviewing all passages gathered so far.",
                "stage_action": (
                    "Integrate the initial passages and the second-hop passages. What specific evidence is still missing? "
                    "Write a concise search query to find it. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What gaps remain after combining the first two sets of evidence? "
                    "What specific term or phrase would help find evidence for the remaining gaps?"
                ),
                "example_reasoning": (
                    "The first two sets of passages establish that X and Y are related, but not causation. "
                    "I need to search for 'Y causes X' or 'causal relationship between Y and X'."
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
                "aim": "Identify the final missing piece of evidence and generate a multi-term query to cast a wider net.",
                "stage_action": (
                    "Integrate all evidence gathered. If there are remaining gaps, write a search query that uses OR "
                    "to combine multiple terms to cover possible variations. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical missing evidence? "
                    "How can we phrase the query with alternative terms (using OR) to maximize recall for the final hop?"
                ),
                "example_reasoning": (
                    "We need evidence for causation. The query should be: 'Y causes X' OR 'X is caused by Y' OR 'causal link Y X'."
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