def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by gathering evidence from Wikipedia. Be precise and focused in your search queries to maximize retrieval of relevant documents. When generating queries, prioritize identifying missing information gaps.",
        "steps": [
            # Step 1: First-hop deep retrieval
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate second-hop query with gap analysis
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information from first-hop evidence and generate precise query",
                "stage_action": "Review retrieved passages and determine key missing information for claim verification. Output ONLY the search query for this missing information, nothing else.",
                "reasoning_questions": "What specific fact is missing?\nWhich entities need verification?\nHow to phrase query for maximum relevance?",
                "example_reasoning": "Claim: 'Marie Curie was the first woman to win a Nobel Prize.'\nPassages: [1] Nobel Prize | First awarded 1901... [2] Marie Curie | Won Physics (1903)...\nMissing: Information about women Nobel winners before 1903.\nQuery: 'first woman Nobel Prize winner before 1903'",
                "dependencies": [1],
            },
            # Step 3: Second-hop deep retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate third-hop query with comprehensive gap analysis
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps using all evidence and generate precise query",
                "stage_action": "Review all retrieved passages (first and second hop) to determine critical missing evidence. Output ONLY the search query for this gap, nothing else.",
                "reasoning_questions": "What new gaps exist after two hops?\nWhich relationships remain unverified?\nHow to avoid redundant queries?",
                "example_reasoning": "Claim: 'Marie Curie was the first woman to win a Nobel Prize.'\nPassages: [1] Nobel facts... [2] Marie Curie wins... [3] 1903 winners...\nMissing: Confirmation of no earlier female winners.\nQuery: 'Nobel Prize female winners 1901-1902'",
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop deep retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify persistent gaps after three hops and generate precise query",
                "stage_action": "Analyze all evidence to find remaining verification gaps. Output ONLY the search query for the missing piece, nothing else.",
                "reasoning_questions": "What evidence is still incomplete?\nWhich aspect has weakest support?\nHow to target the most critical gap?",
                "example_reasoning": "Claim: 'Marie Curie was the first woman to win a Nobel Prize.'\nPassages: [1-5] various facts...\nMissing: Official Nobel records confirming no prior female winners.\nQuery: 'Nobel Prize archives 1901-1902 female laureates'",
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop deep retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Generate fifth-hop query
            {
                "number": 8,
                "title": "Generate fifth-hop query",
                "step_type": "llm",
                "aim": "Identify final verification gaps and generate conclusive query",
                "stage_action": "Determine if any critical evidence remains missing after four hops. Output ONLY the search query for final verification or 'NO_QUERY_NEEDED' if sufficient evidence exists.",
                "reasoning_questions": "Is there any unverifiable claim aspect?\nWhat single piece would confirm/refute?\nWhen to stop querying?",
                "example_reasoning": "Claim: 'Marie Curie was the first woman to win a Nobel Prize.'\nPassages: [1-7] comprehensive coverage...\nMissing: None - all aspects verified.\nQuery: 'NO_QUERY_NEEDED'",
                "dependencies": [1, 3, 5, 7],
            },
            # Step 9: Fifth-hop deep retrieval (conditional on query)
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
        ],
    }