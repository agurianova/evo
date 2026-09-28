def entrypoint():
    return {
        "system_prompt": "You are a multi-hop evidence verifier. Your task is to retrieve all relevant Wikipedia passages needed to verify a claim. Follow these principles:\n- Always break down the claim into key components and verify each part.\n- After each retrieval, summarize the evidence found for that hop only.\n- When generating search queries, focus on specific gaps using precise terms.\n- Prioritize factual accuracy and relevance; avoid speculation.\n- For query generation steps, output ONLY the search query string with no additional text.",
        "steps": [
            # Step 1: First-hop retrieval (standard depth)
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from first-hop passages relevant to the claim",
                "stage_action": (
                    "Read the retrieved passages for this hop and identify the most important facts directly relevant to verifying the claim. "
                    "Produce a concise evidence summary focusing on claim verification. "
                    "Do not include external information or speculate."
                ),
                "reasoning_questions": "",
                "example_reasoning": "",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (broad missing information)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify critical missing information and generate precise query for second hop",
                "stage_action": (
                    "Based on the claim and first-hop evidence summary, identify the most critical missing information. "
                    "Formulate a concise, specific search query targeting this gap. "
                    "Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": "",
                "example_reasoning": "",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (standard depth)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from second-hop passages relevant to the claim",
                "stage_action": (
                    "Read the retrieved passages for this hop and identify the most important facts directly relevant to verifying the claim. "
                    "Produce a concise evidence summary focusing on claim verification. "
                    "Do not include external information or speculate."
                ),
                "reasoning_questions": "",
                "example_reasoning": "",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (specific missing facts)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify precise remaining gap and generate highly specific query for third hop",
                "stage_action": (
                    "Based on all evidence gathered so far (claim, first-hop and second-hop summaries), identify the precise remaining gap. "
                    "Formulate a search query targeting a single fact or relationship using exact entities. "
                    "Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": "",
                "example_reasoning": "",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (deep search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from third-hop passages relevant to the claim",
                "stage_action": (
                    "Read the retrieved passages for this hop and identify the most important facts directly relevant to verifying the claim. "
                    "Produce a concise evidence summary focusing on claim verification. "
                    "Do not include external information or speculate."
                ),
                "reasoning_questions": "",
                "example_reasoning": "",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query (narrow missing piece)
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final missing piece and generate narrow query for fourth hop",
                "stage_action": (
                    "Based on all evidence gathered so far (claim and all hop summaries), identify the exact final missing piece. "
                    "Formulate a highly specific search query using precise terminology and entities. "
                    "Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": "",
                "example_reasoning": "",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deep search)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }