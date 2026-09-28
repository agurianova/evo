def entrypoint():
    return {
        "system_prompt": "You are an expert evidence verifier specializing in multi-hop claim verification. Your role is to guide the retrieval process by generating precise search queries that target missing evidence. At query generation steps, output ONLY the search query string with no additional text. Focus on the most critical gaps in the evidence to verify the claim.",
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
            # Step 2: Generate first query for second hop
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information from the first-hop evidence and formulate a search query to find it.",
                "stage_action": (
                    "Based on the retrieved passages, determine what key fact is missing to verify the claim. "
                    "Write a concise search query to find that fact. Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact stated in the claim is not supported by the retrieved passages?\n"
                    "2. Which entities or relationships should the next query focus on to find the missing fact?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages: 'The Eiffel Tower, completed in 1889, is a wrought-iron lattice tower...'\n"
                    "Missing fact: The exact construction start year is not mentioned; the claim states 1887.\n"
                    "Query: 'Eiffel Tower construction start year'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval (first query)
            {
                "number": 3,
                "title": "Retrieve second-hop passages (first query)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second query for second hop
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after integrating first-hop and initial second-hop evidence, and formulate a refined search query.",
                "stage_action": (
                    "Based on the first-hop passages and the newly retrieved passages, determine what additional evidence is still missing. "
                    "Write a concise search query to find that evidence. Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What new information did the second-hop retrieval provide?\n"
                    "2. What critical gap remains to verify the claim?\n"
                    "3. How can the query be refined to target the remaining gap?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop: 'completed in 1889'\n"
                    "Second-hop (from first query): 'Construction began in January 1887'\n"
                    "Now we have the start year, but the claim says 'built in 1887' which might refer to completion? Actually, the claim is ambiguous. We need to confirm if 'built' means started or completed.\n"
                    "Query: 'Eiffel Tower built meaning construction start or completion'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Second-hop retrieval (second query)
            {
                "number": 5,
                "title": "Retrieve second-hop passages (second query)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate query for third hop
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify any final gaps after two hops and formulate a precise search query for the last retrieval.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine if there is any critical missing evidence. "
                    "Write a concise search query to find it. Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What evidence has been gathered so far?\n"
                    "2. Is there any remaining ambiguity or missing fact that prevents full verification?\n"
                    "3. What is the most precise query to resolve the final gap?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Evidence: Construction began in January 1887 and was completed in 1889.\n"
                    "The claim uses 'built' which might be interpreted as the start year. However, typically 'built' refers to the entire construction period. We need to confirm the common usage.\n"
                    "Query: 'built meaning construction period start or end'"
                ),
                "dependencies": [1, 3, 5],
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