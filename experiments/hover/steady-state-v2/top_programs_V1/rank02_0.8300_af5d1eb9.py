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
                "title": "Generate first query for second hop",
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
                "title": "Generate second query for second hop (distinct gap)",
                "step_type": "llm",
                "aim": "Identify a second critical missing evidence (distinct from first) and generate search query",
                "stage_action": (
                    "Based on the claim, all first-hop retrieved passages, and the first query string (from previous step), "
                    "determine a second critical missing evidence that is distinct from the first gap. "
                    "Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified or no distinct gap exists, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "dependencies": [1, 2],
            },
            {
                "number": 4,
                "title": "Second-hop retrieval (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Second-hop retrieval (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Synthesize evidence and generate query for third hop",
                "step_type": "llm",
                "aim": "Determine if claim verified with current evidence; if not, generate query for third hop",
                "stage_action": (
                    "Synthesize evidence from first hop (step1) and second hop (steps4-5). "
                    "If the claim can be verified, output an empty string. "
                    "Otherwise, generate a concise search query for the most critical missing evidence. "
                    "Output ONLY the query string or empty string."
                ),
                "dependencies": [1, 4, 5],
            },
            {
                "number": 7,
                "title": "Third-hop retrieval (precision-focused)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Synthesize evidence and generate query for fourth hop",
                "step_type": "llm",
                "aim": "Determine if claim verified with current evidence; if not, generate query for fourth hop",
                "stage_action": (
                    "Synthesize evidence from first hop (step1), second hop (steps4-5), and third hop (step7). "
                    "If the claim can be verified, output an empty string. "
                    "Otherwise, generate a concise search query for the most critical missing evidence. "
                    "Output ONLY the query string or empty string."
                ),
                "dependencies": [1, 4, 5, 7],
            },
            {
                "number": 9,
                "title": "Fourth-hop retrieval (precision-focused)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis and verification",
                "step_type": "llm",
                "aim": "Comprehensive verification using all retrieved evidence",
                "stage_action": (
                    "Synthesize all retrieved evidence (steps1,4,5,7,9) to determine if the claim is supported, refuted, or ambiguous. "
                    "Output a brief summary of the evidence and the verification decision. Do not generate any search queries."
                ),
                "dependencies": [1, 4, 5, 7, 9],
            },
        ],
    }