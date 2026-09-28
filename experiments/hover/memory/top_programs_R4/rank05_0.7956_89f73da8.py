def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving supporting evidence from Wikipedia. Your goal is to find all relevant evidence to confirm or refute the claim. Focus on generating precise search queries that target missing evidence.",
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
                "aim": "Identify the first missing piece of evidence needed to verify the claim.",
                "stage_action": (
                    "Analyze the retrieved passages to find what specific fact is missing to verify the claim. "
                    "Write a concise search query for that missing fact. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing from the retrieved passages to verify the claim? "
                    "What entities or relationships should the next query focus on?"
                ),
                "example_reasoning": (
                    "The claim states that 'X caused Y'. The retrieved passages mention X and Y but do not establish causation. "
                    "The missing fact is evidence of causation between X and Y. Query: 'evidence of causation between X and Y'"
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
                "aim": "Identify the next missing piece of evidence given all evidence gathered so far.",
                "stage_action": (
                    "Integrate all retrieved passages to identify what specific fact is still missing to verify the claim. "
                    "Write a concise search query for that missing fact. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is still missing after reviewing all retrieved passages? "
                    "How does this missing fact connect to the claim and the evidence we have?"
                ),
                "example_reasoning": (
                    "We have evidence that X and Y are correlated, but the claim requires causation. "
                    "The missing fact is a study showing that when X occurs, Y follows and there are no confounding factors. "
                    "Query: 'study showing causation between X and Y without confounding factors'"
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
                "aim": "Identify the final missing piece of evidence to fully verify the claim.",
                "stage_action": (
                    "Review all retrieved passages to determine the last specific fact needed to verify the claim. "
                    "Write a concise search query for that missing fact. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the last specific fact required to close the evidence gap? "
                    "What precise information is still missing that would confirm or refute the claim?"
                ),
                "example_reasoning": (
                    "We have evidence of causation in animal studies, but the claim is about humans. "
                    "The missing fact is human clinical trial results. Query: 'human clinical trial results for X causing Y'"
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