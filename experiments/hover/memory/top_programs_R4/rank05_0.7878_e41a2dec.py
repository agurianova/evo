def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker verifying claims by gathering evidence from multiple sources. Your goal is to find all relevant documents to confirm or refute the claim. Focus on identifying missing evidence and generating precise queries.",
        "steps": [
            {
                "number": 1,
                "title": "First-hop retrieval",
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
                "aim": "Identify the most critical missing evidence after the first hop to verify the claim.",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine what specific fact is still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing from the first-hop evidence that is necessary to verify the claim? "
                    "Which entities or relationships need further clarification?"
                ),
                "example_reasoning": (
                    "Example: Claim 'The Eiffel Tower was built in 1887'. First-hop passages mention construction started in 1887 "
                    "but don't state completion. Missing fact: completion year. Query: 'Eiffel Tower completion year'."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Second-hop retrieval",
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
                "aim": "Identify remaining gaps after two hops to verify the claim.",
                "stage_action": (
                    "Based on all evidence gathered so far (first and second hops), determine what specific fact is still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is still missing after reviewing both sets of evidence? "
                    "Are there conflicting details that need resolution? What is the most critical gap for verification?"
                ),
                "example_reasoning": (
                    "Example: Claim 'Marie Curie won two Nobel Prizes'. First-hop: she won in Physics and Chemistry. "
                    "Second-hop: details of the Chemistry prize. Missing: exact year of the Chemistry prize. "
                    "Query: 'Marie Curie Nobel Prize in Chemistry year'."
                ),
                "dependencies": [1, 3],
            },
            {
                "number": 5,
                "title": "Third-hop retrieval",
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
                "aim": "Identify the final missing piece of evidence to verify the claim.",
                "stage_action": (
                    "Based on all evidence gathered so far (three hops), determine what specific fact is still missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Is there any remaining uncertainty? What is the single most critical missing fact? "
                    "If no gaps, output 'NO_QUERY_NEEDED'."
                ),
                "example_reasoning": (
                    "Example: Claim 'The Amazon River is the longest in the world'. First-hop: lists top rivers. "
                    "Second-hop: details on Nile. Third-hop: details on Amazon. Evidence shows Nile is longer. "
                    "Missing: confirmation of current measurements. Query: 'current longest river in the world'. "
                    "If after third hop it's confirmed Amazon is longest, output 'NO_QUERY_NEEDED'."
                ),
                "dependencies": [1, 3, 5],
            },
            {
                "number": 7,
                "title": "Fourth-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }