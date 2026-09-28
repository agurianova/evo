def entrypoint():
    return {
        "system_prompt": "You are a fact-checker verifying claims by retrieving evidence from Wikipedia. Always focus on facts relevant to the claim. For steps that generate a search query, output ONLY the query string with no additional text.",
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
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Write the search query as a single line of text. Your entire response must be "
                    "the query string and nothing else. Do not include any other text, explanations, "
                    "or formatting."
                ),
                "reasoning_questions": (
                    "What specific piece of information is missing to verify the claim? "
                    "How can we phrase a concise search query to find that information?"
                ),
                "example_reasoning": (
                    "The claim states that Marie Curie was born in Paris. The first-hop evidence "
                    "does not mention her birthplace. We need to search for her birthplace. "
                    "Marie Curie birthplace"
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
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Read the second-hop retrieved passages (from step 4) and extract key facts "
                    "relevant to the claim. Then, combine these facts with the first-hop evidence "
                    "summary (from step 2) to produce a unified evidence summary covering all "
                    "relevant facts found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Write the search query as a single line of text. Your entire response must be "
                    "the query string and nothing else. Do not include any other text, explanations, "
                    "or formatting."
                ),
                "reasoning_questions": (
                    "What final piece of information is missing to verify the claim? "
                    "How can we phrase a concise search query to find that information?"
                ),
                "example_reasoning": (
                    "The claim requires knowing the founding year of the International Space Station. "
                    "The evidence so far does not provide it. International Space Station founding year"
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
