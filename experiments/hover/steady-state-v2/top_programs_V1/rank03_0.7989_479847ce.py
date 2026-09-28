def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims via multi-hop evidence retrieval. Focus exclusively on finding evidence directly relevant to the claim. When generating search queries, output ONLY the query string with no additional text.",
        "steps": [
            {
                "number": 1,
                "title": "Initial evidence retrieval (high recall)",
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
                "aim": "Identify most critical missing evidence and generate precise search query",
                "stage_action": (
                    "Based solely on the claim and initial retrieved passages, determine the SINGLE MOST CRITICAL fact needed for verification. "
                    "Write a concise search query targeting ONLY this missing element. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact would most directly verify or refute the claim? "
                    "Which claim element has the weakest supporting evidence in initial passages?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower height is 300m'. Initial passages mention construction date but not height. "
                    "Critical gap: exact height measurement. Query: 'Eiffel Tower exact height in meters'"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "First parallel retrieval (high recall)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate second critical query (distinct)",
                "step_type": "llm",
                "aim": "Identify next critical missing evidence (distinct from first query)",
                "stage_action": (
                    "Based SOLELY on claim and initial passages (ignoring previous queries), determine the NEXT MOST CRITICAL fact needed "
                    "that is DISTINCT from first query's target. Write concise search query. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": (
                    "What important claim element remains unverified after first query? "
                    "How is this gap different from the first identified gap?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower height is 300m'. Initial passages mention height including antennas. "
                    "Critical gap: structural height excluding antennas. Query: 'Eiffel Tower structural height'"
                ),
                "dependencies": [1],
            },
            {
                "number": 5,
                "title": "Second parallel retrieval (high recall)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate third critical query (distinct)",
                "step_type": "llm",
                "aim": "Identify third critical missing evidence (distinct from first two)",
                "stage_action": (
                    "Based SOLELY on claim and initial passages (ignoring previous queries), determine the THIRD CRITICAL fact needed "
                    "that differs from first two queries. Write concise search query. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": (
                    "What remaining ambiguity affects verification? "
                    "Why hasn't this element been covered by initial passages or previous queries?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower height is 300m'. Initial passages lack measurement context. "
                    "Critical gap: year of height measurement. Query: 'Eiffel Tower height measurement year'"
                ),
                "dependencies": [1],
            },
            {
                "number": 7,
                "title": "Third parallel retrieval (high recall)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Evidence synthesis & fourth-hop decision",
                "step_type": "llm",
                "aim": "Assess verification completeness using ALL evidence and determine if fourth hop needed",
                "stage_action": (
                    "Synthesize evidence from initial retrieval and all three parallel branches. "
                    "If claim can be verified with current evidence, output 'NO_QUERY'. "
                    "Otherwise, output search query for the SINGLE MOST CRITICAL remaining gap. "
                    "Output ONLY 'NO_QUERY' or the query string."
                ),
                "reasoning_questions": (
                    "What evidence exists for each claim element? "
                    "What SPECIFIC fact remains unverified and is essential for conclusion?"
                ),
                "example_reasoning": (
                    "Found: height 330m (with antennas), structural height 300m, measured 1889. "
                    "Claim 'height is 300m' is ambiguous. Critical gap: meaning of 'height' in claim. "
                    "Query: 'Eiffel Tower claim 300 meters official definition'"
                ),
                "dependencies": [1, 3, 5, 7],
            },
            {
                "number": 9,
                "title": "Final evidence retrieval (if needed)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
        ],
    }