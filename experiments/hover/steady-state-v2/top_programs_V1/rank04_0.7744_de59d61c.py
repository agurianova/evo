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
                "title": "Filter first-hop passages",
                "step_type": "llm",
                "aim": "Remove irrelevant passages from initial retrieval results",
                "stage_action": (
                    "Review the claim and all retrieved passages. Keep ONLY passages containing "
                    "information directly relevant to verifying the claim. Output filtered passages "
                    "in original format ([i] Title | ...). If none relevant, output 'NO_RELEVANT_PASSAGES'."
                ),
                "reasoning_questions": (
                    "Does this passage provide evidence for/against the claim? "
                    "Is the information directly about the claim's subject or key elements?"
                ),
                "example_reasoning": (
                    "Claim: 'Eiffel Tower height is 300m'. Passage [1] discusses Paris population (irrelevant). "
                    "Passage [2] states 'Eiffel Tower constructed 1889, height 300 meters' (relevant). "
                    "Output: [2] Eiffel Tower | constructed 1889, height 300 meters"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify precise missing evidence and generate search query",
                "stage_action": (
                    "Based on filtered passages and claim, determine what critical evidence is still missing. "
                    "Write a concise search query to find ONLY that missing information. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact would complete verification? "
                    "Which claim element lacks supporting evidence?"
                ),
                "example_reasoning": (
                    "Found: Eiffel Tower built 1889. Missing: height. Query: 'Eiffel Tower exact height in meters'"
                ),
                "dependencies": [1, 2],
            },
            {
                "number": 4,
                "title": "Second-hop retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Filter second-hop passages",
                "step_type": "llm",
                "aim": "Remove irrelevant passages from second retrieval",
                "stage_action": (
                    "Review claim and second-hop passages. Keep ONLY passages containing "
                    "direct evidence for missing elements identified in query. "
                    "Output in original format or 'NO_RELEVANT_PASSAGES'."
                ),
                "reasoning_questions": (
                    "Does this passage address the specific gap identified in the query? "
                    "Is it directly relevant to the missing claim element?"
                ),
                "example_reasoning": (
                    "Query: 'Eiffel Tower height'. Passage [3] discusses construction materials (irrelevant). "
                    "Passage [4] states 'official height 330 meters including antennas'. "
                    "Output: [4] Eiffel Tower | official height 330 meters including antennas"
                ),
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Evidence synthesis & third-hop decision",
                "step_type": "llm",
                "aim": "Assess verification completeness and determine if third hop is needed",
                "stage_action": (
                    "Synthesize evidence from first two hops. If claim can be verified, output 'NO_QUERY'. "
                    "Otherwise, output search query for the single most critical missing fact. "
                    "Output ONLY 'NO_QUERY' or the query string."
                ),
                "reasoning_questions": (
                    "What evidence have we gathered? "
                    "What specific fact remains unverified? "
                    "Is this fact essential for claim verification?"
                ),
                "example_reasoning": (
                    "Found: built 1889, height 330m. Claim requires height without antennas? "
                    "Critical gap: structural height vs total height. Query: 'Eiffel Tower structural height'"
                ),
                "dependencies": [2, 5],
            },
            {
                "number": 7,
                "title": "Third-hop retrieval (high recall)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Filter third-hop passages",
                "step_type": "llm",
                "aim": "Isolate critical evidence for final verification",
                "stage_action": (
                    "Review third-hop passages against the specific gap query. "
                    "Keep ONLY passages resolving the critical missing fact. "
                    "Output in original format or 'NO_RELEVANT_PASSAGES'."
                ),
                "reasoning_questions": (
                    "Does this passage directly answer the precise gap question? "
                    "Is it from a reliable source within Wikipedia?"
                ),
                "example_reasoning": (
                    "Query: 'Eiffel Tower structural height'. Passage [5] states 'main structure height 300m'. "
                    "Output: [5] Eiffel Tower | main structure height 300 meters"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Final evidence synthesis & fourth-hop decision",
                "step_type": "llm",
                "aim": "Confirm verification status and determine if fourth hop is needed",
                "stage_action": (
                    "Synthesize ALL evidence (first three hops). If claim is fully verifiable, output 'NO_QUERY'. "
                    "Otherwise, output search query for the final missing verification element. "
                    "Output ONLY 'NO_QUERY' or the query string."
                ),
                "reasoning_questions": (
                    "With all evidence, what single fact would make verification conclusive? "
                    "Is there any ambiguity remaining in the claim?"
                ),
                "example_reasoning": (
                    "Found: structural height 300m, total 330m. Claim says 'height is 300m' - ambiguous. "
                    "Critical gap: Does claim refer to structural or total height? "
                    "Query: 'Eiffel Tower claim 300 meters meaning'"
                ),
                "dependencies": [2, 5, 8],
            },
            {
                "number": 10,
                "title": "Fourth-hop retrieval (final evidence)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }