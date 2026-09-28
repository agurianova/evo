def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims via multi-hop evidence retrieval. Focus exclusively on finding evidence directly relevant to the claim. When generating search queries, output ONLY the query string with no additional text. If no further evidence is needed, output an empty string.",
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
                "title": "Generate first critical query for second hop",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence and generate search query",
                "stage_action": (
                    "Based on the claim and all first-hop retrieved passages, determine the most critical missing evidence. "
                    "Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified with available evidence, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second critical query for second hop (distinct gap)",
                "step_type": "llm",
                "aim": "Identify a second critical missing evidence (distinct from first) and generate search query",
                "stage_action": (
                    "Based on the claim and all first-hop retrieved passages, determine a second critical missing evidence "
                    "that is distinct from the first gap. Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified with available evidence, output an empty string. "
                    "Output ONLY the query string or empty string."
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
                "title": "Generate first critical query for third hop",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence after second hop and generate search query",
                "stage_action": (
                    "Synthesize evidence from first hop (step1) and second hop (steps4-5). "
                    "Determine the most critical missing evidence. Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Generate second critical query for third hop (distinct gap)",
                "step_type": "llm",
                "aim": "Identify a second critical missing evidence (distinct from first) after second hop and generate search query",
                "stage_action": (
                    "Synthesize evidence from first hop (step1) and second hop (steps4-5). "
                    "Determine a second critical missing evidence that is distinct from the first gap. "
                    "Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 8,
                "title": "Third-hop retrieval (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 9,
                "title": "Third-hop retrieval (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
        ],
    }