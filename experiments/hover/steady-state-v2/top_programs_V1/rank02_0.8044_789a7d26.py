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
                "title": "Assess verification completeness for third hop",
                "step_type": "llm",
                "aim": "Assess if claim can be verified with current evidence; if not, indicate two queries needed",
                "stage_action": (
                    "Synthesize evidence from first hop (step1) and second hop (steps4-5). "
                    "If claim can be verified, output 'NO_QUERY'. "
                    "Otherwise, output 'RETRIEVE_TWO' to indicate two distinct queries are needed for the third hop."
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Generate first third-hop query",
                "step_type": "llm",
                "aim": "Generate first search query for third hop if needed",
                "stage_action": (
                    "If step6 output is 'NO_QUERY', output 'NO_QUERY'. "
                    "Otherwise, based on the claim and all retrieved passages (steps1,4,5), determine the most critical missing evidence. "
                    "Write a concise search query to find ONLY that missing information. "
                    "Output ONLY the query string with no additional text."
                ),
                "dependencies": [1, 4, 5, 6],
            },
            {
                "number": 8,
                "title": "Generate second distinct third-hop query",
                "step_type": "llm",
                "aim": "Generate second distinct search query for third hop if needed",
                "stage_action": (
                    "If step6 output is 'NO_QUERY', output 'NO_QUERY'. "
                    "Otherwise, based on the claim and all retrieved passages (steps1,4,5) and the first query (step7), "
                    "determine a second critical missing evidence that is distinct from the first gap. "
                    "Write a concise search query to find ONLY that missing information. "
                    "Output ONLY the query string with no additional text."
                ),
                "dependencies": [1, 4, 5, 6, 7],
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