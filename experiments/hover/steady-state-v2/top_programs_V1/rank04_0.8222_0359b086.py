def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims via multi-hop evidence retrieval. Focus exclusively on finding evidence directly relevant to the claim. When generating search queries, output ONLY the query string with no additional text. If no further evidence is needed, output an empty string. When identifying gaps for evidence retrieval, ensure they are distinct and cover different aspects of the claim.",
        "steps": [
            {
                "number": 1,
                "title": "First-hop retrieval (high recall)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Centralized gap analysis (first hop)",
                "step_type": "llm",
                "aim": "Identify critical missing evidence gaps from claim and first-hop evidence",
                "stage_action": (
                    "Based on the claim and all first-hop retrieved passages, list up to 2 critical missing evidence gaps. "
                    "Output a JSON object with key 'gaps' containing a list of gap descriptions (strings). "
                    "If no gaps, output {'gaps': []}. "
                    "Output ONLY the JSON object with no additional text."
                ),
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst hop results: [passages about construction]\nOutput: {'gaps': ['Eiffel Tower construction date', 'Eiffel Tower location']}",
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate query for first gap",
                "step_type": "llm",
                "aim": "Generate search query for the first critical gap",
                "stage_action": (
                    "Based on the first gap description from step2, generate a concise search query to find ONLY that missing information. "
                    "If there is no first gap (gaps list empty or <1 element), output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "example_reasoning": "Example gap: 'Eiffel Tower construction date'\nOutput: 'Eiffel Tower construction date year'",
                "dependencies": [1, 2],
            },
            {
                "number": 4,
                "title": "Generate query for second gap",
                "step_type": "llm",
                "aim": "Generate search query for the second critical gap",
                "stage_action": (
                    "Based on the second gap description from step2, generate a concise search query to find ONLY that missing information. "
                    "If there is no second gap (gaps list <2 elements), output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "example_reasoning": "Example gap: 'Eiffel Tower location'\nOutput: 'Eiffel Tower city country'",
                "dependencies": [1, 2],
            },
            {
                "number": 5,
                "title": "Second-hop retrieval (gap 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Second-hop retrieval (gap 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            {
                "number": 7,
                "title": "Generate third-hop query for most critical gap",
                "step_type": "llm",
                "aim": "Identify most critical missing evidence considering all evidence and generate search query",
                "stage_action": (
                    "Based on the claim, first-hop passages (step1), and both second-hop retrieved passages (steps5 and 6), "
                    "determine the most critical missing evidence. Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified with available evidence, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst hop: [construction passages]\nSecond hop branch1: [date passages]\nSecond hop branch2: [location passages]\nMissing: exact construction year confirmation\nOutput: 'Eiffel Tower completed year'",
                "dependencies": [1, 5, 6],
            },
            {
                "number": 8,
                "title": "Generate third-hop query for distinct secondary gap",
                "step_type": "llm",
                "aim": "Identify second critical missing evidence (distinct from first) and generate search query",
                "stage_action": (
                    "Based on the claim, first-hop passages (step1), both second-hop retrieved passages (steps5 and 6), "
                    "and the first third-hop query (step7), determine a second critical missing evidence that is distinct from the first gap. "
                    "Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified or no distinct gap exists, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst hop: [construction passages]\nSecond hop branch1: [date passages]\nSecond hop branch2: [location passages]\nFirst third-hop query: 'Eiffel Tower completed year'\nMissing: confirmation of location city\nOutput: 'Eiffel Tower city'",
                "dependencies": [1, 5, 6, 7],
            },
            {
                "number": 9,
                "title": "Third-hop retrieval (critical gap)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            {
                "number": 10,
                "title": "Third-hop retrieval (secondary gap)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }