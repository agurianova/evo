def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Your task is to verify claims by retrieving supporting evidence from Wikipedia. Perform multi-hop retrieval to maximize coverage of relevant passages. After each retrieval, assess if the evidence is sufficient. When generating search queries, output ONLY the query string without any additional text or explanations.",
        "steps": [
            # Step 1: First-hop retrieval on claim
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate primary second-hop query
            {
                "number": 2,
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence, determine the single most important piece of missing evidence "
                    "needed to verify the claim. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What key fact is missing to verify the claim? How can I phrase a concise query to find it?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "First-hop passages: mention construction in 1889, location, height, but not duration.\n"
                    "Missing: the intended duration. Query: 'Eiffel Tower intended duration'"
                ),
                "dependencies": [1],
            },
            # Step 3: Primary second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve primary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate secondary second-hop query
            {
                "number": 4,
                "title": "Generate secondary second-hop query",
                "step_type": "llm",
                "aim": "Identify an alternative missing information path and generate a search query.",
                "stage_action": (
                    "Based on the first-hop evidence and the results of the primary second-hop retrieval, "
                    "determine a different piece of missing evidence that could support verification. "
                    "Write a concise search query for this alternative path.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What other angle can I explore to find evidence? How is this different from the primary query?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "First-hop: construction details. Primary second-hop: found it was intended for 20 years.\n"
                    "Still missing: why it was kept beyond 20 years? Query: 'Eiffel Tower kept after 20 years reason'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Secondary second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve secondary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 6: Assess sufficiency and generate third-hop query
            {
                "number": 6,
                "title": "Assess evidence sufficiency",
                "step_type": "llm",
                "aim": "Determine if all evidence is gathered; if not, generate a query for the final hop.",
                "stage_action": (
                    "Review all evidence gathered so far (first hop, primary second hop, secondary second hop). "
                    "If the evidence is sufficient to verify the claim, output the exact string: 'NO_QUERY_NEEDED'. "
                    "Otherwise, determine the final missing piece and write a concise search query.\n"
                    "Provide ONLY the query string or 'NO_QUERY_NEEDED', no additional text."
                ),
                "reasoning_questions": "Do we have enough evidence to verify the claim? If not, what single piece is missing?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Evidence: construction in 1889, intended for 20 years, and kept because of radio communication value.\n"
                    "Sufficient? Yes. Output: 'NO_QUERY_NEEDED'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval (conditional)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }