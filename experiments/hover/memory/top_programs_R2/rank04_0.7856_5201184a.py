def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checking assistant. Your task is to verify claims by retrieving relevant evidence from Wikipedia abstracts. Be thorough: identify key entities and missing facts precisely. For query generation steps, output ONLY the search query string with no additional text.",
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
            # Step 2: Generate primary second-hop query
            {
                "number": 2,
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify the primary missing information from first-hop evidence and generate a precise search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine the most critical missing fact needed to verify the claim. "
                    "Focus on key entities and unverified facts. Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "Which key entity in the claim lacks supporting evidence? "
                    "What precise fact is still missing? "
                    "How can we formulate a query using domain-specific terminology to find this fact?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Evidence: [1] Eiffel Tower | ... built for the 1889 World's Fair ...\n"
                    "Missing: intended duration. Query: 'Eiffel Tower original permit duration'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate alternative second-hop query
            {
                "number": 3,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify an alternative missing information path and generate a distinct search query",
                "stage_action": (
                    "Analyze the retrieved passages to find a different angle or alternative missing fact not covered by the first query (from step2). "
                    "Specifically, avoid using the same key terms as the first query. "
                    "Ensure the query is distinct and targets a complementary evidence path. "
                    "Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "What is a different unverified aspect of the claim? "
                    "Which entity or relationship might have an alternative explanation? "
                    "How can we phrase a query that avoids overlap with the first query?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Evidence: [1] Eiffel Tower | ... built for the 1889 World's Fair ...\n"
                    "Alternative missing: whether dismantling occurred as planned. Query: 'Eiffel Tower dismantled after World\\'s Fair'"
                ),
                "dependencies": [1, 2],
            },
            # Step 4: Primary second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve primary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Alternative second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve alternative second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Generate third-hop query from combined evidence
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gaps from combined second-hop results and generate precise query",
                "stage_action": (
                    "Analyze ALL passages from primary and alternative second-hop retrievals to determine the exact missing evidence. "
                    "Focus exclusively on unverified facts and residual gaps. Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "What specific fact remains unverified after reviewing all evidence? "
                    "Which entity should the query target to resolve the claim? "
                    "How can we avoid terms already covered by previous evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Evidence:\n[1] Eiffel Tower | ... built for the 1889 World's Fair ...\n"
                    "[2] Eiffel Tower | ... permit granted for 20 years ...\n"
                    "[3] Eiffel Tower | ... dismantling planned after fair ...\n"
                    "Residual gap: actual dismantling decision. Query: 'Eiffel Tower dismantling decision 1909'"
                ),
                "dependencies": [1, 4, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }