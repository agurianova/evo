def entrypoint():
    return {
        "system_prompt": "You are a fact-checker verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant documents that support or refute the claim.",
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
                "aim": "Identify missing evidence and generate search query for second hop",
                "stage_action": (
                    "Read the retrieved passages and original claim. Identify what specific fact is missing to verify the claim. "
                    "Write a concise search query to find this missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to verify the claim? "
                    "How can we search for it? "
                    "What keywords would best capture the missing information?"
                ),
                "example_reasoning": "",
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
                "aim": "Identify remaining gaps and generate search query for third hop",
                "stage_action": (
                    "Read the original claim and all retrieved passages so far (first and second hop). "
                    "Identify what specific fact is still missing to verify the claim. "
                    "Write a concise search query to find this missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Given all evidence gathered so far, what specific fact is still missing? "
                    "How to search for it? "
                    "What keywords would best capture the missing information?"
                ),
                "example_reasoning": "",
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
                "aim": "Identify final gaps and generate search query for fourth hop",
                "stage_action": (
                    "Read the original claim and all retrieved passages so far (first, second, and third hop). "
                    "Identify what final piece of evidence is needed to verify the claim. "
                    "Write a concise search query to find this evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What final piece of evidence is needed? "
                    "How to search for it? "
                    "What keywords would best capture the missing information?"
                ),
                "example_reasoning": "",
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