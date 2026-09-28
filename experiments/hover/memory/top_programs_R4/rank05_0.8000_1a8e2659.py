def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim. Use sequential multi-hop reasoning: after each retrieval, analyze ALL evidence gathered so far to identify the next critical missing piece of evidence. Generate a precise search query for the next hop that targets ONLY one specific missing fact. Output ONLY the search query with no additional text.",
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
                "aim": "Identify the first critical missing evidence after first hop and generate precise search query for second hop.",
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
                "aim": "After analyzing all evidence retrieved so far (first and second hops), identify the next critical missing evidence and generate a precise search query for the third hop.",
                "stage_action": (
                    "Based on the first-hop and second-hop retrieved passages, determine the next important specific fact still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Given the evidence from the first and second hops, what is the next critical fact still missing? "
                    "Which entity or relationship remains unverified that is essential for the claim?"
                ),
                "example_reasoning": (
                    "The first-hop passages mention Y and the second-hop passages confirm Z, but they do not address W, which is another critical aspect. "
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
                "aim": "After analyzing all evidence retrieved so far (first, second, and third hops), identify any remaining critical missing evidence and generate a precise search query for the fourth hop.",
                "stage_action": (
                    "Based on the first-hop, second-hop, and third-hop retrieved passages, determine if there is any remaining critical specific fact missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "After reviewing all evidence from the first, second, and third hops, is there any remaining critical fact missing? "
                    "What is the final piece of evidence needed to verify the claim?"
                ),
                "example_reasoning": (
                    "The first-hop passages mention Y, the second-hop confirms Z, and the third-hop covers W, but they still lack information about V. "
                    "Therefore, the missing fact is about V. Query: 'V'"
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