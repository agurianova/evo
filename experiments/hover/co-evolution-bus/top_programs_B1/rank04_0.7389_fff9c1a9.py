def entrypoint():
    return {
        "system_prompt": "Multi-hop fact-checker. For query steps: output ONLY plain keywords (no quotes/punctuation). Be concise.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract all key facts and entities from the first-hop passages relevant to the claim.",
                "stage_action": (
                    "List bullet points of key facts and entities (names, dates, locations) from the retrieved passages. One fact per bullet. Do not include any analysis or extra text. Preserve only the most critical facts for verification."
                ),
                "reasoning_questions": (
                    "What specific entities (people, organizations, places, dates) are mentioned? "
                    "What factual claims are made that relate to the claim? "
                    "Which facts are critical for verification and might require further evidence?"
                ),
                "example_reasoning": (
                    "Example: \n- Entity: John Smith\n- Fact: Born in 1980\n- Fact: Won Nobel Prize in 2010\n- Fact: Worked at MIT until 2015"
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate a precise search query targeting the second gold document.",
                "stage_action": (
                    "Based on the bullet-point summary, identify the most critical missing piece of evidence for the second gold document. Output ONLY the search query as a string of plain keywords (no quotes/punctuation), no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact from the claim is not yet supported? "
                    "Which entity or event needs more context? "
                    "What exact term would find the missing document?"
                ),
                "example_reasoning": (
                    "Example: 'John Smith Nobel Prize committee 2010'\nDo not output: 'Query: ...' or any extra text."
                ),
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Combine evidence from first and second hops into a critical fact summary for the final hop.",
                "stage_action": (
                    "Extract key facts and entities from the second-hop passages (step4 output) and integrate with the first-hop summary (step2 output). List bullet points of all critical facts. One fact per bullet. Do not include analysis. Preserve only the most critical facts for verification."
                ),
                "reasoning_questions": (
                    "What new facts and entities are in the second-hop passages? "
                    "How do they connect to the first-hop facts? "
                    "What is the single most critical remaining gap for the claim?"
                ),
                "example_reasoning": (
                    "Example: \nFrom step4: extract 'Jane Doe worked at NIH' and 'Jane Doe was committee member'. \nIntegrated summary: \n- Entity: John Smith\n- Fact: Born in 1980\n- Fact: Won Nobel Prize in 2010\n- Entity: Jane Doe\n- Fact: Worked at NIH\n- Fact: Nobel committee member"
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a highly specific search query targeting the third gold document.",
                "stage_action": (
                    "Based on the integrated evidence, identify the single most critical missing piece of evidence for the third gold document. Output ONLY the search query as a string of plain keywords (no quotes/punctuation), no additional text."
                ),
                "reasoning_questions": (
                    "What is the one remaining fact that is essential and not yet verified? "
                    "Which entity or relationship is most distant from the claim? "
                    "What exact terms would retrieve the third gold document?"
                ),
                "example_reasoning": (
                    "Example: 'Jane Doe NIH Nobel Prize committee 2010'\nDo not output: 'Query: ...' or any extra text."
                ),
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
