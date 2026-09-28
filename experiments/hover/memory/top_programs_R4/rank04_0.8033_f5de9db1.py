def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Your task is to verify claims by retrieving supporting evidence from Wikipedia. Perform multi-hop retrieval: start with the claim, then use retrieved evidence to formulate new queries for additional evidence. Focus exclusively on finding all relevant supporting documents.",
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
            # Step 2: Generate first second-hop query with decomposition
            {
                "number": 2,
                "title": "Generate first second-hop query with decomposition",
                "step_type": "llm",
                "aim": "Decompose the claim into atomic sub-claims and identify the first missing evidence piece",
                "stage_action": (
                    "1. Break the claim into 2-3 independent, verifiable sub-claims.\n"
                    "2. Based on the first-hop retrieved passages, determine which sub-claim lacks supporting evidence.\n"
                    "3. Write a concise search query focused on verifying that specific sub-claim.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What are the atomic facts in the claim? Which sub-claim is not supported by the first-hop passages?",
                "example_reasoning": (
                    "Example: Claim 'Marie Curie won two Nobel Prizes in Physics (1903) and Chemistry (1911)'.\n"
                    "Sub-claims: (1) Marie Curie won the Nobel Prize in Physics in 1903; (2) Marie Curie won the Nobel Prize in Chemistry in 1911.\n"
                    "First-hop passages confirm (1) but not (2). Query: <Marie Curie Nobel Prize Chemistry 1911>"
                ),
                "dependencies": [1],
            },
            # Step 3: First second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve with first second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second second-hop query with decomposition
            {
                "number": 4,
                "title": "Generate second second-hop query with decomposition",
                "step_type": "llm",
                "aim": "Decompose the claim into atomic sub-claims and identify a different missing evidence piece",
                "stage_action": (
                    "1. Break the claim into 2-3 independent, verifiable sub-claims (same decomposition as step2).\n"
                    "2. Based on the first-hop retrieved passages, determine a different sub-claim that lacks evidence (distinct from step2's target).\n"
                    "3. Write a concise search query focused on verifying that specific sub-claim.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What are the atomic facts in the claim? Which sub-claim, different from step2's focus, is not supported by the first-hop passages?",
                "example_reasoning": (
                    "Example: Claim 'Marie Curie won two Nobel Prizes in Physics (1903) and Chemistry (1911)'.\n"
                    "Sub-claims: (1) Marie Curie won the Nobel Prize in Physics in 1903; (2) Marie Curie won the Nobel Prize in Chemistry in 1911.\n"
                    "First-hop passages confirm (2) but not (1). Query: <Marie Curie Nobel Prize Physics 1903>"
                ),
                "dependencies": [1],
            },
            # Step 5: Second second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve with second second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps across all evidence and generate final query",
                "stage_action": (
                    "Based on all evidence gathered (steps 1,3,5), determine the critical missing piece for verification. "
                    "Write a concise search query for the third-hop retrieval.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "Given all passages, what specific fact is still missing to confirm the claim? What is the final verification gap?",
                "example_reasoning": "Example: Evidence confirms event date but not location. Query: <Battle of Hastings location>",
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }