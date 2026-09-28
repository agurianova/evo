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
            # Step 2: Decompose claim and generate first second-hop query
            {
                "number": 2,
                "title": "Decompose claim and generate first second-hop query",
                "step_type": "llm",
                "aim": "Decompose the claim into atomic sub-claims, then identify the first missing evidence piece and generate a search query",
                "stage_action": (
                    "First, break the claim into 2-3 atomic sub-claims. Then, based on the first-hop retrieved passages, determine which sub-claim lacks evidence and what specific information is missing. "
                    "Write a concise search query for the first missing piece.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What atomic sub-claims make up the claim? Which sub-claim has the most critical missing evidence in the first-hop passages?",
                "example_reasoning": (
                    "Example: Claim 'Marie Curie won two Nobel Prizes in 1903 and 1911'. "
                    "Decomposition: [1] Marie Curie won a Nobel Prize in 1903. [2] Marie Curie won a Nobel Prize in 1911. "
                    "First-hop passages confirm she won two prizes but not the years. "
                    "Missing: years for sub-claim 1. Query: <Marie Curie first Nobel Prize year>"
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
            # Step 4: Decompose claim and generate second second-hop query
            {
                "number": 4,
                "title": "Decompose claim and generate second second-hop query",
                "step_type": "llm",
                "aim": "Decompose the claim into atomic sub-claims, then identify a different missing evidence piece targeting new entities and generate alternative query",
                "stage_action": (
                    "First, break the claim into 2-3 atomic sub-claims. Then, based solely on the first-hop passages (step1), identify a DIFFERENT sub-claim that lacks evidence (distinct from step2's focus). "
                    "Write a concise search query for this alternative missing piece.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What atomic sub-claims make up the claim? Which sub-claim (other than step2's focus) has missing evidence? How can you target a distinct knowledge gap?",
                "example_reasoning": (
                    "Example: Claim 'Marie Curie won two Nobel Prizes in 1903 and 1911'. "
                    "Decomposition: [1] Marie Curie won a Nobel Prize in 1903. [2] Marie Curie won a Nobel Prize in 1911. "
                    "First query (step2) targeted the first year. Now target the second year: Query: <Marie Curie second Nobel Prize year>"
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