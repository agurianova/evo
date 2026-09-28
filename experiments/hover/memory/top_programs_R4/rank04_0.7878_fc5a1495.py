def entrypoint():
    return {
        "system_prompt": "You are a fact-checker verifying claims by retrieving relevant evidence from Wikipedia. Your goal is to find all supporting documents for the claim.",
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the specific missing fact from the first-hop evidence needed to verify the claim.",
                "stage_action": (
                    "Analyze the retrieved passages and determine what single piece of evidence is missing to verify the claim. "
                    "Write a concise search query to find this missing evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing from the first-hop evidence to verify the claim? "
                    "Which entities or relationships need further support?"
                ),
                "example_reasoning": (
                    "The claim states that 'X invented Y in 1900'. The first-hop passages confirm X's work on Y but don't mention the year. "
                    "Missing fact: the exact year of invention. Query: 'year X invented Y'."
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
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after integrating first and second-hop evidence.",
                "stage_action": (
                    "Based on all evidence retrieved so far, determine the next missing piece of evidence required to verify the claim. "
                    "Write a concise search query for this evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Given the evidence from the first two hops, what specific fact is still missing? "
                    "How does the new evidence from the second hop change the remaining gaps?"
                ),
                "example_reasoning": (
                    "The claim requires evidence of Z's involvement. First hop shows X and Y, second hop shows Y and Z but not the connection to the event. "
                    "Missing fact: Z's role in the event. Query: 'Z involvement in event'."
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
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing piece after three hops of evidence.",
                "stage_action": (
                    "After reviewing all evidence gathered, determine the one remaining piece of information needed to fully verify the claim. "
                    "Write a concise search query for this final evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "After three hops, what is the single most critical missing fact? "
                    "Which part of the claim remains unverified?"
                ),
                "example_reasoning": (
                    "The claim states 'A caused B via C'. Evidence covers A and B, and A and C, but not the causal chain through C. "
                    "Missing fact: how C mediates A causing B. Query: 'mechanism of A causing B through C'."
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