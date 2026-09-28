def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checking assistant. Your task is to verify claims by retrieving and analyzing evidence from Wikipedia. Always be precise and focus on finding factual evidence. For query generation steps, output ONLY the search query string with no additional text.",
        "steps": [
            # Step 1: First-hop retrieval
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information from the first-hop evidence and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the claim and the first-hop retrieved passages, determine what additional evidence is needed. "
                    "Output ONLY the search query string to find the missing evidence. Do not add any other text."
                ),
                "reasoning_questions": (
                    "What specific facts are mentioned in the claim but not supported by the first-hop evidence? "
                    "Which entities or events need further verification? "
                    "What precise terms should be used in the query to find the missing evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887 and is located in Paris.'\n"
                    "First-hop evidence: [1] Paris | The capital of France. [2] Eiffel Tower | Built in 1889.\n"
                    "Missing: The construction year (1887 vs 1889) and location (already confirmed as Paris).\n"
                    "Query: 'Eiffel Tower construction year'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
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
                "aim": "Identify remaining gaps after two hops and generate a precise search query for the third hop.",
                "stage_action": (
                    "Integrate the claim and evidence from the first two hops. Determine what specific evidence is still missing. "
                    "Output ONLY the search query string to find the missing evidence. Do not add any other text."
                ),
                "reasoning_questions": (
                    "What aspects of the claim are still unverified after two hops? "
                    "Which entities or events require further evidence? "
                    "How can we phrase a query that targets the exact missing information?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won Nobel Prizes in Physics and Chemistry in 1903 and 1911.'\n"
                    "First-hop: [1] Marie Curie | Nobel Prize in Physics 1903. [2] Nobel Prize | Marie Curie also won in Chemistry.\n"
                    "Second-hop: [1] Chemistry Nobel | Awarded to Marie Curie in 1911.\n"
                    "Missing: Confirmation of the year 1911 for Chemistry.\n"
                    "Query: 'Marie Curie Nobel Prize Chemistry year'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Gap analysis and fourth-hop query
            {
                "number": 6,
                "title": "Gap analysis and fourth-hop query",
                "step_type": "llm",
                "aim": "Assess if evidence from three hops fully verifies the claim. If not, generate query for fourth hop; otherwise indicate no more hops.",
                "stage_action": (
                    "Review the claim and all retrieved evidence (first, second, and third hops). "
                    "If the claim is fully supported or refuted, output 'NO_MORE_HOPS'. "
                    "Otherwise, determine the specific missing evidence and output ONLY the search query string to find it. "
                    "Do not add any other text."
                ),
                "reasoning_questions": (
                    "Does the evidence cover every part of the claim? "
                    "What specific fact is still missing? "
                    "If nothing is missing, output 'NO_MORE_HOPS'. "
                    "If something is missing, what precise query will retrieve the missing fact?"
                ),
                "example_reasoning": (
                    "Claim: 'The Amazon River is the longest river in the world at 6400 km.'\n"
                    "First-hop: [1] Amazon River | Second longest river.\n"
                    "Second-hop: [1] Nile River | Longest river at 6650 km.\n"
                    "Third-hop: [1] River lengths | Amazon is 6400 km, Nile is 6650 km.\n"
                    "Missing: Confirmation that the Nile is longer (which refutes the claim). Evidence is sufficient to refute.\n"
                    "Output: 'NO_MORE_HOPS'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }