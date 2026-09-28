def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Always be precise and focused. When generating search queries, aim for clarity and relevance to the missing evidence. When summarizing, extract only the most relevant facts for verifying the claim.",
        "steps": [
            # Step 1: First-hop retrieval (broad)
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
                "aim": "Extract key facts from the first-hop retrieved passages that are directly relevant to verifying the claim.",
                "stage_action": (
                    "Read the retrieved passages from the first hop and identify the most important facts that support or refute the claim. "
                    "Produce a concise summary of these facts. Do not include any information not present in the passages."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (broad for initial gap)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information after the first hop and generate a broad search query for the second hop.",
                "stage_action": (
                    "Based on the claim and the first-hop evidence summary, determine what key information is still missing to verify the claim. "
                    "Formulate a search query that is broad enough to cover potential evidence sources but specific to the gap. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep for gap-filling)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages that are directly relevant to verifying the claim.",
                "stage_action": (
                    "Read the retrieved passages from the second hop and identify the most important facts that support or refute the claim. "
                    "Produce a concise summary of these facts. Do not include any information not present in the passages."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (specific for precise gap)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the precise missing fact after the first two hops and generate a specific search query for the third hop.",
                "stage_action": (
                    "Based on the claim and the evidence summaries from the first and second hops, determine the exact missing piece of evidence needed to verify the claim. "
                    "Formulate a highly specific search query targeting that fact. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (deep for precise gap)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages that are directly relevant to verifying the claim.",
                "stage_action": (
                    "Read the retrieved passages from the third hop and identify the most important facts that support or refute the claim. "
                    "Produce a concise summary of these facts. Do not include any information not present in the passages."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            # Step 9: Decide fourth hop (adaptive termination)
            {
                "number": 9,
                "title": "Check evidence completeness",
                "step_type": "llm",
                "aim": "Determine if all necessary evidence has been gathered or if a fourth hop is needed to verify the claim.",
                "stage_action": (
                    "Review the evidence summaries from the first, second, and third hops. "
                    "If the claim can be verified with the current evidence, output 'TERMINATE'. "
                    "Otherwise, identify the exact missing piece of evidence and formulate a highly specific search query for it. "
                    "Provide ONLY the query or 'TERMINATE', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deep for final gap)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }