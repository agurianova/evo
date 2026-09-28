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
                    "Based on the first-hop retrieved passages, determine what specific fact in the claim lacks supporting evidence. "
                    "Write a concise search query to retrieve evidence for this missing fact.\n"
                    "Output Format: The entire response must be ONLY the query string.\n"
                    "Example output: Albert Einstein birth year\n"
                    "Do not include any other text, explanations, or formatting."
                ),
                "reasoning_questions": "What specific fact in the claim is not supported by the first-hop passages? What is the most direct query to find that fact?",
                "example_reasoning": (
                    "Claim: 'Albert Einstein was born in 1879'.\n"
                    "Passages: [1] Einstein developed the theory of relativity in 1905. [2] He received the Nobel Prize in 1921.\n"
                    "Analysis: Passages confirm scientific work but omit birth details. Missing fact: birth year.\n"
                    "Query: Albert Einstein birth year"
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
            # Step 4: Generate second second-hop query
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different missing evidence piece targeting new entities/aspects and generate an orthogonal query",
                "stage_action": (
                    "Based on the first-hop retrieved passages, identify a different missing fact than the first query (targeting distinct entities or aspects). "
                    "Write a concise search query for this new evidence gap.\n"
                    "Output Format: The entire response must be ONLY the query string.\n"
                    "Example output: Albert Einstein birth place\n"
                    "Do not include any other text, explanations, or formatting."
                ),
                "reasoning_questions": "What is a different fact (or aspect) in the claim not covered by evidence so far? How can we target a distinct entity or perspective from the first query?",
                "example_reasoning": (
                    "Claim: 'Albert Einstein was born in Ulm, Germany in 1879'.\n"
                    "Passages: [1] Einstein's theory of relativity. [2] Nobel Prize details.\n"
                    "Analysis: First query targeted birth year (1879). Now target birth location (Ulm). Missing aspect: geographical context.\n"
                    "Query: Albert Einstein birth place"
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
                "aim": "Identify remaining evidence gaps after two hops and generate final query",
                "stage_action": (
                    "Based on all evidence gathered (first-hop and both second-hop retrievals), determine the final missing piece for full verification. "
                    "Write a concise search query targeting this remaining gap.\n"
                    "Output Format: The entire response must be ONLY the query string.\n"
                    "Example output: Albert Einstein birth certificate\n"
                    "Do not include any other text, explanations, or formatting."
                ),
                "reasoning_questions": "Given all evidence, what specific detail remains unverified? How can we formulate a query that targets the last missing element?",
                "example_reasoning": (
                    "Claim: 'Albert Einstein was born on March 14, 1879 in Ulm'.\n"
                    "Evidence: Confirms 1879 and Ulm, but not exact date (March 14).\n"
                    "Analysis: Need primary source documentation for precise date.\n"
                    "Query: Albert Einstein birth certificate"
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