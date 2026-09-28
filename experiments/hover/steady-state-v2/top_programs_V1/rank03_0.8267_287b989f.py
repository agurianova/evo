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
                "reasoning_questions": "What evidence is still missing? List top 2 gaps. Which gap is most critical?",
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst query: 'Eiffel Tower construction date'\nFirst hop results: [passages about construction]\nSecond gap: location (distinct from date). Query: 'Eiffel Tower location'",
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
                "title": "Generate first query for third hop",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence from first branch and generate search query",
                "stage_action": (
                    "Based on the claim, the first-hop retrieved passages (step1), and the second-hop branch 1 passages (step4), "
                    "determine the most critical missing evidence. "
                    "Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified with available evidence, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "reasoning_questions": "What evidence is still missing? List the top 2 gaps. Which gap is most critical to verify the claim?",
                "dependencies": [1, 4],
            },
            {
                "number": 7,
                "title": "Generate second query for third hop (distinct gap)",
                "step_type": "llm",
                "aim": "Identify a second critical missing evidence (distinct from first) and generate search query",
                "stage_action": (
                    "Based on the claim, the first-hop retrieved passages (step1), the second-hop branch 2 passages (step5), "
                    "and the first third-hop query (from step6), determine a second critical missing evidence that is distinct from the first gap. "
                    "Write a concise search query to find ONLY that missing information. "
                    "If claim can be verified or no distinct gap exists, output an empty string. "
                    "Output ONLY the query string or empty string."
                ),
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\nFirst query: 'Eiffel Tower construction date'\nFirst hop results: [passages about construction]\nSecond gap: location (distinct from date). Query: 'Eiffel Tower location'",
                "dependencies": [1, 5, 6],
            },
            {
                "number": 8,
                "title": "Third-hop retrieval (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            {
                "number": 9,
                "title": "Third-hop retrieval (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            {
                "number": 10,
                "title": "Final evidence synthesis and verification",
                "step_type": "llm",
                "aim": "Comprehensive verification using all retrieved evidence",
                "stage_action": (
                    "Synthesize all retrieved evidence (steps1,4,5,8,9) to determine if the claim is supported, refuted, or ambiguous. "
                    "Output a brief summary of the evidence and the verification decision. Do not generate any search queries."
                ),
                "dependencies": [1, 4, 5, 8, 9],
            },
        ],
    }