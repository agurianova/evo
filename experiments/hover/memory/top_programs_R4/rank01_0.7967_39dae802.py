def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim.",
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
                "aim": "Identify missing evidence after first hop and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine what specific fact is missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing from the first-hop evidence to verify the claim? "
                    "Which entities or relationships need further exploration?"
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
                "aim": "Identify missing evidence after two hops and generate a precise search query for the third hop.",
                "stage_action": (
                    "Based on all evidence from first and second hops, determine what specific fact is still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing now? How does the new evidence from the second hop change the gaps? "
                    "Which entities or relationships are still unverified?"
                ),
                "example_reasoning": (
                    "The first two hops cover A and B but do not address C, which is critical for the claim. "
                    "The missing fact is about C. Query: 'C'"
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
                "aim": "Identify the final missing evidence and generate a precise search query for the fourth hop.",
                "stage_action": (
                    "Based on all evidence from first, second, and third hops, determine the final piece of evidence needed to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the last missing fact? Has all other evidence been gathered? "
                    "Which specific detail is still absent?"
                ),
                "example_reasoning": (
                    "All evidence so far supports the claim except for the detail about D. "
                    "The final missing fact is D. Query: 'D'"
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