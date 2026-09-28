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
                    "Query: 'Barack Obama birth city Honolulu'")
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
                "aim": "Identify a different line of evidence (not covered by branch A) needed to verify the claim and generate a precise search query for it",
                "stage_action": (
                    "Based on the claim, first-hop passages, and the first branch of second-hop passages, determine a distinct missing piece of evidence. "
                    "Write a concise search query targeting this evidence without overlapping with branch A. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Given the first-hop passages and the first branch of second-hop passages, what is a DIFFERENT piece of evidence still missing? "
                    "How can the query be formulated to avoid the topics already covered by the first branch?"
                ),
                "example_reasoning": (
                    "Claim: 'Barack Obama was born in Honolulu.' First-hop: mentions 'Hawaii'. First branch of second-hop: found 'Honolulu' as birth city. "
                    "Now missing: official documentation. Query: 'Barack Obama birth certificate Hawaii Department of Health'")
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
            # Step 6: Generate query for third hop or skip
            {
                "number": 6,
                "title": "Generate query for third hop or skip",
                "step_type": "llm",
                "aim": "Determine if the claim is fully verified by the retrieved passages. If yes, output an empty string. Otherwise, identify missing evidence and generate a precise search query for the third hop.",
                "stage_action": (
                    "Review the claim and all retrieved passages (first hop and both branches of second hop). "
                    "If the evidence is sufficient to verify the claim, output an empty string. "
                    "Otherwise, write a concise search query for the missing evidence. "
                    "Provide ONLY the search query (or empty string), no additional text."
                ),
                "reasoning_questions": (
                    "Do the retrieved passages (from hop1 and both branches of hop2) provide sufficient evidence to verify the claim? "
                    "If yes, why? If no, what specific evidence is still missing? "
                    "How can the query be formulated to target the missing evidence, or should we skip if complete?"
                ),
                "example_reasoning": (
                    "Example 1 (evidence complete):\n"
                    "Claim: 'Barack Obama was born in Honolulu.'\n"
                    "Passages:\n"
                    "  [1] 'Barack Obama was born in Hawaii.'\n"
                    "  [3] 'He was born in Honolulu, the capital of Hawaii.'\n"
                    "  [5] 'The birth certificate is on file with the Hawaii Department of Health.'\n"
                    "All evidence is present. Output: ''\n\n"
                    "Example 2 (evidence incomplete):\n"
                    "Claim: 'Barack Obama was born in Honolulu.'\n"
                    "Passages:\n"
                    "  [1] 'Barack Obama was born in Hawaii.'\n"
                    "  [3] 'He was born in Honolulu, the capital of Hawaii.'\n"
                    "  [5] 'The birth certificate exists but lacks verification details.'\n"
                    "Missing: official verification. Query: 'Barack Obama birth certificate verification official document'")
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