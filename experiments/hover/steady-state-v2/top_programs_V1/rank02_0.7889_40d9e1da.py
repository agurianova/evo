def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims via multi-hop evidence retrieval. Focus exclusively on finding evidence directly relevant to the claim. When generating search queries, output ONLY the query string with no additional text.",
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
                "title": "Generate first critical query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence and generate search query",
                "stage_action": (
                    "Based on the claim and all first-hop retrieved passages, determine the most critical missing evidence. "
                    "Write a concise search query to find ONLY that missing information. "
                    "Output ONLY the query string with no additional text."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second critical query (distinct gap)",
                "step_type": "llm",
                "aim": "Identify a second critical missing evidence (distinct from first) and generate search query",
                "stage_action": (
                    "Based on the claim and all first-hop retrieved passages, determine a second critical missing evidence "
                    "that is distinct from the first gap. Write a concise search query to find ONLY that missing information. "
                    "Output ONLY the query string with no additional text."
                ),
                "dependencies": [1],
            },
            {
                "number": 4,
                "title": "Second-hop retrieval (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Second-hop retrieval (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Evidence synthesis after second hop",
                "step_type": "llm",
                "aim": "Assess verification completeness and determine if third hop is needed",
                "stage_action": (
                    "Synthesize evidence from first hop (step1) and second hop (steps4-5). "
                    "If claim can be verified, output 'NO_QUERY'. Otherwise, output search query for the single most critical missing fact. "
                    "Output ONLY 'NO_QUERY' or the query string."
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Third-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Evidence synthesis after third hop",
                "step_type": "llm",
                "aim": "Assess verification completeness and determine if fourth hop is needed",
                "stage_action": (
                    "Synthesize evidence from all hops (steps1,4,5,7). "
                    "If claim can be verified, output 'NO_QUERY'. Otherwise, output search query for the single most critical missing fact. "
                    "Output ONLY 'NO_QUERY' or the query string."
                ),
                "dependencies": [1, 4, 5, 7],
            },
            {
                "number": 9,
                "title": "Fourth-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis",
                "step_type": "llm",
                "aim": "Confirm verification status (no further retrieval)",
                "stage_action": (
                    "Synthesize all evidence from steps1,4,5,7,9. "
                    "Output 'NO_QUERY' to indicate no further retrieval is possible."
                ),
                "dependencies": [1, 4, 5, 7, 9],
            },
        ],
    }