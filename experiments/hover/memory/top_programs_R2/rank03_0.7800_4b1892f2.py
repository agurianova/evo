def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checking assistant. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Always be precise and thorough. When generating search queries, focus on key entities and relationships mentioned in the claim and the retrieved evidence. Use specific terminology to maximize retrieval relevance.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve initial evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the claim and the first-hop passages, determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key entities or relationships in the claim are not addressed by the first-hop passages? "
                    "What specific Wikipedia article titles or topics might contain the missing evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.' First-hop passages mention construction starting in 1887 but not completion. "
                    "Missing: completion date. Query: 'Eiffel Tower completion date'."
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a precise search query for the third hop, considering evidence from first two hops.",
                "stage_action": (
                    "Integrate evidence from first-hop and second-hop passages. Determine what final piece of evidence is still needed. "
                    "Write a concise search query to find this evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact or detail is still missing after reviewing both sets of passages? "
                    "Which entities or relationships require further clarification? "
                    "What precise Wikipedia topic would contain the missing information?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes.' First-hop: mentions Nobel Prizes in Physics and Chemistry. "
                    "Second-hop: details about the Physics prize. Missing: details about the Chemistry prize. "
                    "Query: 'Marie Curie Nobel Prize in Chemistry'."
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify any remaining gaps and generate a precise search query for the fourth hop.",
                "stage_action": (
                    "Review all retrieved passages from first, second, and third hops. Determine if missing evidence exists. "
                    "Write a concise search query to find the missing evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "After three hops, what is the most critical missing piece of evidence? "
                    "Are there any ambiguities or unverified aspects of the claim? "
                    "What specific Wikipedia article or section would resolve this?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919.' First three hops cover signing date, location, and major terms. "
                    "Missing: the exact day of the month. Query: 'Treaty of Versailles signing day'."
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }