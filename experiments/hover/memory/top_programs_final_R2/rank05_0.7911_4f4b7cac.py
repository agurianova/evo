def entrypoint():
    return {
        "system_prompt": "You are a fact-checking assistant. Your task is to generate precise search queries for retrieving evidence to verify claims. Focus on key entities and specific terminology to maximize retrieval coverage. For query generation steps, output ONLY the search query string with no additional text.",
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
            # Step 2: Generate first query for second hop (branch A)
            {
                "number": 2,
                "title": "Generate first query for second hop (branch A)",
                "step_type": "llm",
                "aim": "Identify one distinct line of evidence needed to verify the claim and generate a precise search query for it",
                "stage_action": (
                    "Based on the claim and first-hop passages, determine one critical missing piece of evidence. "
                    "Write a concise search query targeting this evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical piece of evidence missing from the first-hop passages to verify the claim? "
                    "What specific entities or context can form a precise query for this evidence without overlapping with other potential evidence paths?"
                ),
                "example_reasoning": (
                    "Claim: 'Barack Obama was born in Honolulu.' First-hop passages mention 'Hawaii' but not the exact birth location. "
                    "Query: 'Barack Obama birth city Honolulu'"),
                "dependencies": [1],
            },
            # Step 3: First branch of second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve first branch of second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second query for second hop (branch B)
            {
                "number": 4,
                "title": "Generate second query for second hop (branch B)",
                "step_type": "llm",
                "aim": "Identify either a distinct evidence path or refined query for remaining gaps",
                "stage_action": (
                    "Based on the claim, first-hop passages, and the first branch of second-hop passages, determine if there is a distinct missing piece of evidence. "
                    "If so, write a query for it. If not, write a refined query targeting the same gap with higher precision to obtain more specific details. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Given the first-hop passages and the first branch of second-hop passages, is there a distinct piece of evidence still missing? "
                    "If yes, what is it and how to formulate a query avoiding the first branch? If not, how to refine the query for the same gap to get more specific details?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was completed on March 31, 1889.'\n"
                    "First-hop: [1] 'The Eiffel Tower is located in Paris, France.'\n"
                    "First branch of second-hop: [3] 'It was completed in 1889.'\n"
                    "The first branch confirms the year but not the exact date. Query: 'Eiffel Tower completion date March 31 1889'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Second branch of second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve second branch of second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate focused query for third hop (single missing piece)
            {
                "number": 6,
                "title": "Generate focused query for third hop",
                "step_type": "llm",
                "aim": "Identify the single most critical missing piece of evidence needed to verify the claim",
                "stage_action": (
                    "Review the claim, first-hop passages (step1), and second-hop passages (steps 3 and 5). "
                    "Identify the single most critical missing piece of evidence. "
                    "Write a concise search query targeting this evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Based on all retrieved evidence (first and second hops), what is the single most critical missing piece of evidence to verify the claim? "
                    "How can the query be formulated to target this specific gap without broadening scope?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was completed on March 31, 1889.'\n"
                    "First-hop passages: [1] 'The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France.'\n"
                    "Second-hop passages:\n"
                    "  [3] 'Construction began in 1887 and was completed in 1889.'\n"
                    "  [5] 'It was built for the 1889 World\'s Fair.'\n"
                    "Missing: exact completion date (March 31). Query: 'Eiffel Tower completion date March 31 1889'"
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