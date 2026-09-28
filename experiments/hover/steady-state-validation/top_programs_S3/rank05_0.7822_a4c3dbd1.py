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
            # Step 2: First-hop retrieval (upgraded to deep retrieval)
            {
                "number": 2,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
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
            # Step 4: Primary second-hop retrieval
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
            # Step 5: Generate alternative second-hop query (conditional)
            {
                "number": 5,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify complementary missing evidence only if primary path is insufficient",
                "stage_action": (
                    "Using first-hop and primary second-hop passages, determine if there is a complementary verification path not covered by the primary second-hop. "
                    "If primary second-hop already covers necessary evidence, output empty string. "
                    "Otherwise, output ONLY the search query for the complementary gap, no additional text."
                ),
                "reasoning_questions": (
                    "What other evidence could verify the claim? "
                    "Has the primary second-hop already answered the critical question?"
                ),
                "example_reasoning": (
                    "First-hop: Confirms NASA mission but not crew\n"
                    "Primary second-hop: Confirms launch date and astronauts\n"
                    "Output: ''"
                ),
                "dependencies": [2, 4],
            },
            # Step 6: Alternative second-hop retrieval
            {
                "number": 6,
                "title": "Retrieve alternative second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 7: List missing evidence (new dedicated step)
            {
                "number": 7,
                "title": "List missing evidence",
                "step_type": "llm",
                "aim": "Identify all specific gaps in evidence after reviewing all passages",
                "stage_action": (
                    "Review passages from steps 2,4,6. List every missing piece of evidence required to verify the claim. "
                    "Be specific about what facts are still missing. Output format: 'Gap 1: ...\nGap 2: ...'"
                ),
                "reasoning_questions": (
                    "What verifiable facts are still absent? "
                    "Which specific claims lack supporting evidence?"
                ),
                "example_reasoning": (
                    "Step2: Apollo 11 mission overview\n"
                    "Step4: Launch date confirmed\n"
                    "Step6: Astronaut names confirmed\n"
                    "Gap 1: Moon landing photographic evidence\n"
                    "Gap 2: Lunar module specifications"
                ),
                "dependencies": [2, 4, 6],
            },
            # Step 8: Evidence sufficiency check (simplified)
            {
                "number": 8,
                "title": "Check evidence sufficiency",
                "step_type": "llm",
                "aim": "Determine if all evidence gaps are closed",
                "stage_action": (
                    "Based on the missing evidence list (step7), if there are no gaps, output 'SUFFICIENT'. "
                    "Otherwise, output 'INSUFFICIENT'. Output ONLY the word 'SUFFICIENT' or 'INSUFFICIENT'."
                ),
                "reasoning_questions": (
                    "Does the missing evidence list contain any items? "
                    "Is every required fact verified?"
                ),
                "example_reasoning": (
                    "Missing evidence list: Gap 1: Moon landing photographic evidence\n"
                    "Output: 'INSUFFICIENT'"
                ),
                "dependencies": [7],
            },
            # Step 9: Generate third-hop query (conditional on gaps)
            {
                "number": 9,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Create query for most critical gap if evidence insufficient",
                "stage_action": (
                    "If step8 output is 'INSUFFICIENT', generate search query for the most critical gap from step7. "
                    "If 'SUFFICIENT', output empty string. Output ONLY the query string or empty string."
                ),
                "reasoning_questions": (
                    "What single missing fact would most conclusively verify the claim? "
                    "How to phrase the query for maximum relevance?"
                ),
                "example_reasoning": (
                    "Step7: Gap 1: Moon landing photographic evidence\n"
                    "Step8: 'INSUFFICIENT'\n"
                    "Query: 'Apollo 11 moon landing photographic proof'"
                ),
                "dependencies": [7, 8],
            },
            # Step 10: Third-hop deep retrieval
            {
                "number": 10,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }
