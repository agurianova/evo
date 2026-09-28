def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checking assistant. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Always base your queries on specific entities and relationships mentioned in the claim and retrieved evidence. Be precise and avoid vague terms.",
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
                "aim": "Identify missing information from first-hop evidence and generate precise second-hop query",
                "stage_action": (
                    "Analyze the retrieved passages to determine what specific evidence is still needed to verify the claim. "
                    "Focus on key entities and relationships not yet supported. Generate a concise, precise search query "
                    "using specific terminology. Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific entities or relationships in the claim lack supporting evidence from the retrieved passages?\n"
                    "2. What precise terms should be used to retrieve evidence about these gaps?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built using iron from mines in Alsace.'\n"
                    "Retrieved passages: [0] Eiffel Tower | The Eiffel Tower is a wrought-iron lattice tower ...\n"
                    "Analysis: Evidence confirms material (wrought-iron) and location (Paris) but not iron source (Alsace).\n"
                    "Missing: Source of iron.\n"
                    "Query: 'Eiffel Tower iron source Alsace mines'"
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
                "aim": "Identify remaining gaps using all evidence and generate precise third-hop query",
                "stage_action": (
                    "Analyze all retrieved passages (first and second hop) to determine what specific evidence is still missing. "
                    "Focus on unverified entities/relationships. Generate a concise, precise search query using specific "
                    "terminology. Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific aspects of the claim remain unverified by the combined evidence?\n"
                    "2. What precise terms will retrieve evidence for these remaining gaps?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won Nobel Prizes in both Physics and Chemistry.'\n"
                    "Passages: [0] Marie Curie | ... first woman to win a Nobel Prize ...\n"
                    "          [1] Nobel Prize in Physics | ... awarded for discovery of radioactivity ...\n"
                    "Analysis: Evidence confirms Physics prize but not Chemistry prize.\n"
                    "Missing: Chemistry Nobel Prize.\n"
                    "Query: 'Marie Curie Nobel Prize Chemistry'"
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
            # Step 6: Generate fourth-hop query with gap analysis
            {
                "number": 6,
                "title": "Generate fourth-hop query with gap analysis",
                "step_type": "llm",
                "aim": "Determine if evidence is complete or generate fourth-hop query for remaining gaps",
                "stage_action": (
                    "Analyze all retrieved passages (first, second, and third hop) to determine if the claim is fully verified. "
                    "If evidence is complete, output exactly 'DONE'. Otherwise, identify specific missing evidence and "
                    "generate a concise, precise search query. Provide ONLY the query string or 'DONE', no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific aspects of the claim are still unverified by all evidence gathered?\n"
                    "2. If no gaps exist, output 'DONE'. Otherwise, what precise terms should be used for the final query?"
                ),
                "example_reasoning": (
                    "Claim: 'The Pacific Ocean is the largest and deepest ocean on Earth.'\n"
                    "Passages: [0] Pacific Ocean | ... largest ocean ...\n"
                    "          [1] Pacific Ocean | ... average depth 3,970 meters ...\n"
                    "          [2] Ocean depth | Challenger Deep in Pacific is 10,925 meters ...\n"
                    "Analysis: Evidence confirms largest size and depth records. No gaps.\n"
                    "Output: 'DONE'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval (conditional)
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