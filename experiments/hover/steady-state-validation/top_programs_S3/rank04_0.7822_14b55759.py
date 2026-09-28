def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims through multi-hop evidence retrieval. Be precise: when generating search queries, output ONLY the query string with no additional text. If no query is needed, output an empty string. Always prioritize concise, evidence-focused queries.",
        "steps": [
            # Step 1: Generate optimized first-hop query
            {
                "number": 1,
                "title": "Generate first-hop query",
                "step_type": "llm",
                "aim": "Reformulate claim into concise, effective search query",
                "stage_action": (
                    "Transform the claim into a concise but contextually rich search query that captures the full verification context. "
                    "Prioritize including key entities and relationships for comprehensive first-hop results. "
                    "Output ONLY the query string, no additional text or explanations."
                ),
                "reasoning_questions": (
                    "What is the central verifiable fact? "
                    "Which keywords maximize evidence retrieval?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969'\n"
                    "Query: 'Apollo 11 moon landing mission date'"
                ),
                "dependencies": [],
            },
            # Step 2: First-hop retrieval (switched to standard for precision)
            {
                "number": 2,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[0]"},
                },
                "dependencies": [1],
            },
            # Step 3: Generate primary second-hop query
            {
                "number": 3,
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify key missing evidence from first-hop results",
                "stage_action": (
                    "Based on first-hop passages, determine the most critical missing verification fact. "
                    "Output ONLY the search query for this specific gap, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence directly supports/refutes the claim? "
                    "Which gap prevents definitive verification?"
                ),
                "example_reasoning": (
                    "First-hop: Mentions Apollo 11 but not launch date\n"
                    "Query: 'Apollo 11 launch date'"
                ),
                "dependencies": [2],
            },
            # Step 4: Primary second-hop retrieval (deep for recall)
            {
                "number": 4,
                "title": "Retrieve primary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Gap analysis with criticality ordering
            {
                "number": 5,
                "title": "List missing evidence by criticality",
                "step_type": "llm",
                "aim": "Identify all specific gaps in evidence and rank by criticality",
                "stage_action": (
                    "Review passages from first-hop (step2) and primary second-hop (step4). List every missing piece of evidence "
                    "required to verify the claim, in order of criticality (most critical first). "
                    "Output format: 'Gap 1: ...\nGap 2: ...'"
                ),
                "reasoning_questions": (
                    "What specific facts are missing from the first-hop results? "
                    "What specific facts are missing from the primary second-hop results? "
                    "Which missing fact is most critical for verification?"
                ),
                "example_reasoning": (
                    "First-hop: Apollo 11 mission overview (mentions crew but not launch date)\n"
                    "Primary second-hop: Launch date confirmed (July 16, 1969)\n"
                    "Gap 1: Exact time of moon landing\n"
                    "Gap 2: Names of astronauts who walked on the moon"
                ),
                "dependencies": [2, 4],
            },
            # Step 6: Generate query for top gap
            {
                "number": 6,
                "title": "Generate query for most critical gap",
                "step_type": "llm",
                "aim": "Create search query for the top missing evidence gap",
                "stage_action": (
                    "Based on the gap list (step5), generate a search query for the first gap (most critical). "
                    "If there are no gaps, output empty string. Output ONLY the query string, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical missing fact? "
                    "How to phrase the query for maximum relevance?"
                ),
                "example_reasoning": (
                    "Gap list: Gap 1: Moon landing photographic evidence\n"
                    "Query: 'Apollo 11 moon landing photographic proof'"
                ),
                "dependencies": [5],
            },
            # Step 7: Retrieve for top gap
            {
                "number": 7,
                "title": "Retrieve for most critical gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            # Step 8: Generate query for second gap
            {
                "number": 8,
                "title": "Generate query for second critical gap",
                "step_type": "llm",
                "aim": "Create search query for the second most critical evidence gap",
                "stage_action": (
                    "Based on the gap list (step5), generate a search query for the second gap (if exists). "
                    "If there is only one gap or none, output empty string. Output ONLY the query string, no additional text."
                ),
                "reasoning_questions": (
                    "What is the second most critical missing fact? "
                    "How to phrase the query for maximum relevance?"
                ),
                "example_reasoning": (
                    "Gap list: Gap 1: Moon landing photographic evidence\n"
                    "Gap 2: Lunar module specifications\n"
                    "Query: 'Apollo 11 lunar module specifications'"
                ),
                "dependencies": [5],
            },
            # Step 9: Retrieve for second gap
            {
                "number": 9,
                "title": "Retrieve for second critical gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }
