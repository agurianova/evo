def entrypoint():
    return {
        "system_prompt": (
            "You are an expert fact-checker verifying claims using Wikipedia evidence. "
            "Be precise: when generating search queries, output ONLY the query string with no additional text. "
            "When summarizing evidence, focus strictly on facts relevant to the claim. "
            "Always prioritize factual accuracy over completeness."
        ),
        "steps": [
            # Step 1: Generate first-hop query
            {
                "number": 1,
                "title": "Generate first-hop query",
                "step_type": "llm",
                "aim": "Create an effective initial search query from the claim",
                "stage_action": (
                    "Analyze the claim to identify key entities and relationships. "
                    "Generate a concise, focused search query optimized for Wikipedia retrieval. "
                    "Output ONLY the search query string, no additional text or explanations."
                ),
                "reasoning_questions": "What are the central entities? What specific fact needs verification?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended as a temporary installation.' "
                "Key entities: Eiffel Tower, temporary installation. "
                'Query: "Eiffel Tower original purpose temporary"',
                "dependencies": [],
            },
            # Step 2: First-hop retrieval (deep)
            {
                "number": 2,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate a targeted query to address gaps in the initial evidence",
                "stage_action": (
                    "Analyze the claim and the retrieved passages to identify missing evidence. "
                    "Generate a precise search query for the next retrieval. "
                    "Output ONLY the query string, no additional text."
                ),
                "reasoning_questions": "What evidence is missing to verify the claim? What specific terms would find it?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended as a temporary installation.' "
                "Passages: [Eiffel Tower] 'Built for 1889 World's Fair', [Paris] 'Hosted World's Fair'. "
                'Missing: permit duration. Query: "Eiffel Tower construction permit duration"',
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Generate third-hop query
            {
                "number": 5,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a query to address remaining gaps after two hops",
                "stage_action": (
                    "Integrate evidence from all previous retrievals. "
                    "Identify specific missing facts needed to verify the claim. "
                    "Generate a precise search query. Output ONLY the query string."
                ),
                "reasoning_questions": "What critical information is still missing? How can we formulate a query to find it?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended as a temporary installation.' "
                "Passages: ... Missing: exact permit expiration. "
                'Query: "Eiffel Tower permit expiration date 1889"',
                "dependencies": [2, 4],
            },
            # Step 6: Third-hop retrieval (deep)
            {
                "number": 6,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [5],
            },
            # Step 7: Generate fourth-hop query
            {
                "number": 7,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a query for the fourth hop to cover residual evidence gaps",
                "stage_action": (
                    "Review all evidence gathered so far. "
                    "Identify the most critical missing information. "
                    "Generate a highly focused query. Output ONLY the query string."
                ),
                "reasoning_questions": "What is the most specific gap remaining? What primary source might confirm it?",
                "example_reasoning": "Claim: ... Missing: official document stating 'temporary'. "
                'Query: "Eiffel Tower original construction documents temporary"',
                "dependencies": [2, 4, 6],
            },
            # Step 8: Fourth-hop retrieval (deep)
            {
                "number": 8,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Generate fifth-hop query
            {
                "number": 9,
                "title": "Generate fifth-hop query",
                "step_type": "llm",
                "aim": "Generate a final query to capture any remaining evidence",
                "stage_action": (
                    "Assess the completeness of the evidence. "
                    "If gaps remain, generate a query targeting the most specific missing detail. "
                    "Otherwise, generate a broad query: 'claim [claim text]' to capture any peripheral evidence. "
                    "Output ONLY the query string."
                ),
                "reasoning_questions": "Is there any unverified aspect? What narrow query would find the last piece?",
                "example_reasoning": "Claim: ... Verified: 20-year permit. Unverified: original intention. "
                'Query: "Eiffel Tower Gustave Eiffel temporary statement"',
                "dependencies": [2, 4, 6, 8],
            },
            # Step 10: Fifth-hop retrieval (deep)
            {
                "number": 10,
                "title": "Retrieve fifth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }
