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
                "title": "Gap analysis after first hop",
                "step_type": "llm",
                "aim": "Identify up to two distinct critical missing evidence gaps",
                "stage_action": "Based on the claim and the first-hop retrieved passages, identify up to two distinct critical missing evidence gaps. Output a JSON list of the gaps (e.g., ['gap1 description', 'gap2 description']). If no gaps, output empty list [].",
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst-hop results: [passages about construction date]\nThus, the gaps are: ['location of Eiffel Tower', 'height of Eiffel Tower']",
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate query for first gap (second hop)",
                "step_type": "llm",
                "aim": "Generate search query for the first gap",
                "stage_action": "Based on the claim, the first-hop retrieved passages, and the first gap from the gap analysis (step2), write a concise search query to find ONLY that missing information. Output ONLY the query string or empty string if no query needed.",
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst-hop results: [passages about construction date]\nGap analysis: ['location of Eiffel Tower', 'height of Eiffel Tower']\nFirst gap: 'location of Eiffel Tower'\nOutput: Eiffel Tower location",
                "dependencies": [1, 2],
            },
            {
                "number": 4,
                "title": "Generate query for second gap (second hop)",
                "step_type": "llm",
                "aim": "Generate search query for the second gap (if exists)",
                "stage_action": "Based on the claim, the first-hop retrieved passages, and the second gap from the gap analysis (step2), write a concise search query to find ONLY that missing information. Output ONLY the query string or empty string if no query needed or if only one gap exists.",
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst-hop results: [passages about construction date]\nGap analysis: ['location of Eiffel Tower', 'height of Eiffel Tower']\nSecond gap: 'height of Eiffel Tower'\nOutput: Eiffel Tower height",
                "dependencies": [1, 2],
            },
            {
                "number": 5,
                "title": "Second-hop retrieval (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Second-hop retrieval (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            {
                "number": 7,
                "title": "Generate first query for third hop",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence from all available evidence and generate search query",
                "stage_action": "Based on the claim, the first-hop retrieved passages (step1), and both second-hop retrieved passages (steps5 and 6), determine the most critical missing evidence. Write a concise search query to find ONLY that missing information. Output ONLY the query string or empty string.",
                "dependencies": [1, 5, 6],
            },
            {
                "number": 8,
                "title": "Generate second query for third hop",
                "step_type": "llm",
                "aim": "Identify a second critical missing evidence (distinct from first) and generate search query",
                "stage_action": "Based on the claim, the first-hop retrieved passages (step1), both second-hop retrieved passages (steps5 and 6), and the first third-hop query (from step7), determine a second critical missing evidence that is distinct from the first gap. Write a concise search query to find ONLY that missing information. Output ONLY the query string or empty string.",
                "dependencies": [1, 5, 6, 7],
            },
            {
                "number": 9,
                "title": "Third-hop retrieval (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            {
                "number": 10,
                "title": "Third-hop retrieval (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }