def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your task is to verify claims by retrieving supporting evidence from Wikipedia. At each step, carefully analyze the provided evidence summary to identify critical missing facts, then generate precise, concise search queries (2-4 terms) to fill those gaps. When generating multiple queries for the same hop, ensure they target distinct aspects of the missing evidence.",
        "steps": [
            # Step 1: First-hop deep retrieval
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence and gaps
            {
                "number": 2,
                "title": "Summarize first-hop evidence and gaps",
                "step_type": "llm",
                "aim": "Distill the retrieved evidence into a concise summary of verified facts and critical gaps",
                "stage_action": (
                    "Review the retrieved passages and write a 1-2 sentence summary of what has been verified and what specific facts are still missing. "
                    "Focus on gaps that are essential for claim verification."
                ),
                "reasoning_questions": (
                    "1. What key facts from the claim are confirmed by the evidence?\n"
                    "2. What specific, critical details are still missing?\n"
                    "3. How can we phrase the missing facts as search targets?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes in different scientific fields.'\n"
                    "Retrieved: [1] Nobel Prize | ... [2] Physics | ...\n"
                    "Summary: Confirmed Marie Curie won Nobel Prizes. Missing: the specific fields (e.g., Physics and Chemistry) and the years."
                ),
                "dependencies": [1],
            },
            # Step 3a: Generate first second-hop query
            {
                "number": 3,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence and generate a precise search query for the second hop",
                "stage_action": (
                    "Based on the evidence summary, determine the single most important fact still missing to verify the claim. "
                    "Write a concise search query (2-4 terms) targeting ONLY this missing fact. "
                    "Provide ONLY the search query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What is the most critical unverified detail?\n"
                    "2. Which entity or event should the query target?\n"
                    "3. How can we phrase this in 2-4 terms for maximum recall?"
                ),
                "example_reasoning": (
                    "Summary: Confirmed Marie Curie won Nobel Prizes. Missing: the specific fields (e.g., Physics and Chemistry) and the years.\n"
                    "Query: 'Marie Curie Nobel Prize fields'"
                ),
                "dependencies": [2],
            },
            # Step 3b: Generate second second-hop query
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different critical missing evidence and generate a precise search query for the second hop",
                "stage_action": (
                    "Based on the evidence summary, determine a different important fact (not covered by the first query) that is still missing. "
                    "Write a concise search query (2-4 terms) targeting ONLY this missing fact. "
                    "Provide ONLY the search query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What is another critical unverified detail (distinct from the first query's target)?\n"
                    "2. Which aspect of the claim requires verification?\n"
                    "3. How can we phrase this in 2-4 terms for maximum recall?"
                ),
                "example_reasoning": (
                    "Summary: Confirmed Marie Curie won Nobel Prizes. Missing: the specific fields (e.g., Physics and Chemistry) and the years.\n"
                    "Query: 'Marie Curie Nobel Prize years'"
                ),
                "dependencies": [2],
            },
            # Step 4: Retrieve second-hop passages for first query
            {
                "number": 5,
                "title": "Retrieve second-hop passages for first query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Retrieve second-hop passages for second query
            {
                "number": 6,
                "title": "Retrieve second-hop passages for second query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 6: Summarize combined evidence and remaining gaps
            {
                "number": 7,
                "title": "Summarize combined evidence and remaining gaps",
                "step_type": "llm",
                "aim": "Synthesize all evidence so far and identify remaining verification gaps",
                "stage_action": (
                    "Combine the initial evidence summary and the new evidence from the second hop. "
                    "Write a concise summary (1-2 sentences) of verified facts and remaining critical gaps."
                ),
                "reasoning_questions": (
                    "1. What new facts have been verified by the second-hop evidence?\n"
                    "2. What critical details are still missing?\n"
                    "3. How do the missing facts relate to the original claim?"
                ),
                "example_reasoning": (
                    "Initial summary: Confirmed Marie Curie won Nobel Prizes. Missing: fields and years.\n"
                    "New evidence from first query: [1] Physics | ...\n"
                    "New evidence from second query: [1] 1903 | ...\n"
                    "Summary: Confirmed Nobel Prize in Physics (1903). Missing: the second field (Chemistry) and its year (1911)."
                ),
                "dependencies": [2, 5, 6],
            },
            # Step 7: Generate third-hop query
            {
                "number": 8,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical remaining missing evidence and generate a precise search query for the third hop",
                "stage_action": (
                    "Based on the combined evidence summary, determine the single most important fact still missing. "
                    "Write a concise search query (2-4 terms) targeting ONLY this missing fact. "
                    "Provide ONLY the search query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What is the most critical unverified detail now?\n"
                    "2. Which entity or event should the query target?\n"
                    "3. How can we phrase this in 2-4 terms for maximum recall?"
                ),
                "example_reasoning": (
                    "Summary: Confirmed Nobel Prize in Physics (1903). Missing: the second field (Chemistry) and its year (1911).\n"
                    "Query: 'Marie Curie Nobel Prize Chemistry 1911'"
                ),
                "dependencies": [7],
            },
            # Step 8: Retrieve third-hop passages
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }