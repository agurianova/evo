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
                "aim": "Identify the most critical missing evidence piece by decomposing the claim and generate a search query",
                "stage_action": (
                    "Break the claim into its key atomic assertions. For each assertion, check if it is supported by the first-hop passages. "
                    "Identify the most critical missing assertion. Write a concise search query to verify that assertion. "
                    "Avoid including specific numbers or years unless they are explicitly stated in the claim and missing in the evidence. "
                    "Focus on entities and general relationships.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What are the atomic assertions in the claim? Which one is most critical and missing in the evidence? Which key entity or relationship requires verification?",
                "example_reasoning": (
                    "Example 1: Claim states 'Marie Curie won two Nobel Prizes'. First-hop passages confirm the prizes but not the years. "
                    "Query: <Marie Curie Nobel Prize years>\n"
                    "Example 2: Claim states 'The Eiffel Tower is located in Paris'. First-hop passages confirm the tower but not the location. "
                    "Query: <Eiffel Tower location>"
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
                "aim": "Identify a distinct missing evidence piece by decomposing the claim and generate an alternative search query",
                "stage_action": (
                    "Break the claim into its key atomic assertions. Step2 likely targeted the most critical gap (e.g., the primary entity's attribute). "
                    "Now, identify a different missing assertion that involves a distinct entity or aspect. "
                    "Write a concise search query for that. Avoid redundancy with the first query and avoid over-specification.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "What atomic assertions remain after considering the most critical gap? Which entity or aspect (other than the primary one) requires verification? How can you target a knowledge gap that is complementary to the first query?",
                "example_reasoning": (
                    "Example 1: First query was about birth year. Claim also mentions major achievement. "
                    "Query: <Albert Einstein theory of relativity year>\n"
                    "Example 2: First query was about the location of the Eiffel Tower. Claim also mentions the height. "
                    "Query: <Eiffel Tower height>"
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
                "aim": "Identify the final critical missing piece across all evidence and generate the third-hop query",
                "stage_action": (
                    "Review all evidence gathered (steps 1, 3, 5). Break the claim into atomic assertions and check which are still missing. "
                    "Identify the single most critical missing fact that prevents full verification. "
                    "Write a concise search query for that fact, avoiding over-specification.\n"
                    "Format your response as: <query>"
                ),
                "reasoning_questions": "Given all passages, which atomic assertion of the claim is still missing? What is the minimal additional fact needed for verification? Which entity or relationship is the bottleneck?",
                "example_reasoning": (
                    "Example 1: Evidence confirms event date but not location. Query: <Battle of Hastings location>\n"
                    "Example 2: Evidence confirms the Nobel Prize winner but not the category. Query: <Marie Curie Nobel Prize category>"
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