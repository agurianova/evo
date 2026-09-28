def entrypoint():
    return {
        "system_prompt": "You are a fact-checking assistant. Your goal is to maximize the retrieval of supporting evidence for claim verification by generating precise search queries and analyzing evidence across multiple hops. Always prioritize finding all relevant gold standard documents.",
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
            # Step 2: Analyze first hop and generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify key facts from first-hop passages and determine critical missing evidence for verification.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to the claim. Identify the most critical missing information "
                    "and write a search query to find it. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact or evidence is missing to verify the claim based on the first-hop passages? "
                    "What entities or relationships should the next query focus on?"
                ),
                "example_reasoning": (
                    "The claim states that X. The first-hop passages mention Y but do not confirm Z, which is crucial for X. "
                    "Therefore, the next query should search for 'Z AND [related term]'."
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
            # Step 4: Analyze first+second hops and generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Synthesize evidence from first two hops and identify remaining gap for third hop.",
                "stage_action": (
                    "Review all retrieved passages from the first two hops. Identify the most critical missing evidence "
                    "and write a search query to find it. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence is still missing after reviewing both the first and second hop passages? "
                    "Are there multiple possible paths to the missing evidence?"
                ),
                "example_reasoning": (
                    "After two hops, we have evidence for A and B but not for C, which is necessary for the claim. "
                    "Since C could be related to D or E, the query should be 'C AND (D OR E)'."
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
            # Step 6: Analyze all hops and generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing piece after three hops and generate a comprehensive search query.",
                "stage_action": (
                    "Review all retrieved passages from the first three hops. Determine the last critical piece of evidence needed "
                    "and write a search query to find it. The query may include multiple terms connected by OR to cover alternative paths. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "Are there alternative ways this evidence might be described or related concepts that should be included?"
                ),
                "example_reasoning": (
                    "We have evidence for A, B, and C, but the claim requires confirmation of D. "
                    "Since D might be referred to as 'D' or 'E' in sources, the query should be 'D OR E'."
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