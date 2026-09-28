def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim. Use multi-hop reasoning: after each retrieval, analyze all evidence gathered so far to identify the next critical missing fact. Generate a precise search query for that specific missing fact. When generating queries, focus on one specific missing fact per query and output ONLY the search query.",
        "steps": [
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
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the first critical missing evidence after initial retrieval and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine the most important specific fact missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical fact missing from the first-hop evidence? "
                    "Which entity or relationship is most essential to verify next?"
                ),
                "example_reasoning": (
                    "The claim states 'X'. The first-hop passages mention Y but do not confirm Z, which is required for verification. "
                    "Therefore, the missing fact is about Z. Query: 'Z'"
                ),
                "dependencies": [1],
            },
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
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Analyze all evidence gathered so far (first and second hop) to identify the next critical missing evidence and generate a precise search query for the third hop.",
                "stage_action": (
                    "Based on the first-hop and second-hop retrieved passages, determine the most important specific fact still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence has been gathered so far? What critical fact is still missing? "
                    "Which entity or relationship is most essential to verify next that hasn't been confirmed yet?"
                ),
                "example_reasoning": (
                    "The claim states 'X'. The first-hop passages mention Y and the second-hop passages confirm Z, but do not address W which is required for verification. "
                    "Therefore, the missing fact is about W. Query: 'W'"
                ),
                "dependencies": [1, 3],
            },
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
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Analyze all evidence gathered so far (first, second, and third hop) to identify the final critical missing evidence and generate a precise search query for the fourth hop.",
                "stage_action": (
                    "Based on all retrieved passages from prior hops, determine the last critical specific fact missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence has been gathered across all hops? What is the last critical fact missing? "
                    "Which specific detail is needed to complete the verification?"
                ),
                "example_reasoning": (
                    "After reviewing the first, second, and third hop passages, we have confirmed Y, Z, and V, but the claim also requires evidence about U. "
                    "The passages do not mention U. Therefore, the missing fact is about U. Query: 'U'"
                ),
                "dependencies": [1, 3, 5],
            },
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