def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier for multi-hop claims. Always prioritize recall over precision. Your goal is to find as many relevant supporting documents as possible. When generating search queries, focus on missing information and use precise entity names.",
        "steps": [
            # Step 1: First-hop retrieval with deep recall
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
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
            },
            # Step 3: Generate second-hop query with scaffolding
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information after first hop and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, determine what specific fact is missing to "
                    "verify the claim. Write a concise search query to find this missing information.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities or relationships need further exploration?",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1887.' Evidence: 'The Eiffel Tower was completed in 1889.' Missing: exact construction start date. Query: 'Eiffel Tower construction start year'",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval with deep recall
            {
                "number": 4,
                "title": "Retrieve second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Combine first and second hop evidence (using raw passages)
            {
                "number": 5,
                "title": "Combine first and second hop evidence",
                "step_type": "llm",
                "aim": "Integrate evidence from first and second hops into a unified summary.",
                "stage_action": (
                    "Using the raw passages from the first-hop retrieval and the second-hop retrieval, "
                    "identify all relevant facts supporting the claim verification. Produce a comprehensive "
                    "evidence summary covering connections between hops."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query with scaffolding
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after two hops and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the combined evidence from the first two hops, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise search query to "
                    "find this evidence.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What critical fact is still missing? Which entity or relationship has not been sufficiently verified?",
                "example_reasoning": "Claim: 'Marie Curie won two Nobel Prizes.' Combined evidence: 'Marie Curie won the Nobel Prize in Physics in 1903 and shared it with Pierre Curie and Henri Becquerel.' Missing: the second Nobel Prize (in Chemistry, 1911). Query: 'Marie Curie second Nobel Prize year'",
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval with deep recall
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Generate fourth-hop query with scaffolding
            {
                "number": 8,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after three hops and generate a search query for the fourth hop.",
                "stage_action": (
                    "Based on the combined evidence from the first two hops and the third-hop passages, "
                    "determine what additional evidence is still needed to fully verify the claim. "
                    "Write a concise search query to find this missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific information is still missing? Which part of the claim lacks supporting evidence?",
                "example_reasoning": "Claim: 'The Treaty of Versailles was signed in 1919.' Combined evidence from first two hops: 'The Treaty of Versailles ended World War I.' Third-hop passages: 'The treaty was negotiated in Paris.' Missing: exact signing date. Query: 'Treaty of Versailles signing date'",
                "dependencies": [5, 7],
            },
            # Step 9: Fourth-hop retrieval with deep recall
            {
                "number": 9,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
        ],
    }