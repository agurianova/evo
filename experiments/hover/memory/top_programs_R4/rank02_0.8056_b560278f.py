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
            # Step 2: Generate first second-hop query
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the first missing evidence piece and generate a search query",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query for the first second-hop retrieval.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What specific information from the claim is missing in the first-hop passages? Which key entity requires verification?",
                "example_reasoning": (
                    "Example 1 (Person claim): Claim states 'Marie Curie won two Nobel Prizes'. First-hop passages confirm the prizes but not the categories. Query: <Marie Curie Nobel Prize categories>\n\n"
                    "Example 2 (Event claim): Claim states 'The moon landing occurred in 1969'. First-hop passages confirm the year but not the mission name. Query: <Apollo 11 moon landing mission>"
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
            # Step 4: Generate second second-hop query (now parallel)
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different missing evidence piece targeting new entities and generate alternative query",
                "stage_action": (
                    "Based solely on the first-hop passages (step1), identify a missing evidence piece involving different entities than the first query. "
                    "Write a concise search query for an alternative second-hop retrieval.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What entity or aspect in the claim hasn't been addressed by the first query? How can you target a distinct knowledge gap?",
                "example_reasoning": (
                    "Example 1 (Person claim): First query was about Marie Curie's Nobel categories. Claim also mentions her birth year. Query: <Marie Curie birth year>\n\n"
                    "Example 2 (Event claim): First query was about Apollo 11 mission name. Claim also mentions the landing date. Query: <Apollo 11 moon landing date>"
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
                "example_reasoning": (
                    "Example 1 (Person claim): Evidence confirms Marie Curie won Physics and Chemistry prizes but not the years. Query: <Marie Curie Nobel Prize years>\n\n"
                    "Example 2 (Event claim): Evidence confirms Apollo 11 landed on moon but not the astronaut names. Query: <Apollo 11 astronauts>"
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
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }