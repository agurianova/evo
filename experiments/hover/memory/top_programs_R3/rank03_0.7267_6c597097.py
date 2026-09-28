def entrypoint():
    return {
        "system_prompt": (
            "You are an expert fact-checker verifying claims using Wikipedia evidence. "
            "Your goal is to maximize retrieval of supporting documents. "
            "For query generation steps: output ONLY the search query string or 'NO_QUERY_NEEDED' with no additional text. "
            "For summarization steps: be concise and focus only on facts directly relevant to the claim."
        ),
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from first-hop passages relevant to the claim.",
                "stage_action": (
                    "Read retrieved passages and identify facts directly relating to claim verification. "
                    "Produce a concise summary of these facts."
                ),
                "reasoning_questions": (
                    "1. What specific claims in these passages are relevant to the target claim?\n"
                    "2. Which facts are most critical for verification (e.g., dates, locations, events)?"
                ),
                "example_reasoning": (
                    "Target claim: 'Albert Einstein was born in Germany.'\n"
                    "Passages: \n"
                    "  [1] Albert Einstein was a theoretical physicist. \n"
                    "  [2] He was born in Ulm, in the Kingdom of Württemberg in the German Empire.\n"
                    "Relevant fact: born in Ulm, Germany. \n"
                    "Summary: Albert Einstein was born in Ulm, Germany."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate precise search query for second hop.",
                "stage_action": (
                    "Based on the first-hop summary, determine additional evidence needed to verify the claim. "
                    "Write a concise search query to find missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is missing from the first-hop summary?\n"
                    "2. What keywords would best retrieve evidence for this missing fact?"
                ),
                "example_reasoning": (
                    "Claim: 'Albert Einstein was born in Germany.' \n"
                    "First-hop summary: Albert Einstein was a theoretical physicist. \n"
                    "Missing fact: birthplace. \n"
                    "Query: Albert Einstein birthplace"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from second-hop passages relevant to the claim.",
                "stage_action": (
                    "Read retrieved passages and identify facts directly relating to claim verification. "
                    "Produce a concise summary of these facts."
                ),
                "reasoning_questions": (
                    "1. What specific claims in these passages are relevant to the target claim?\n"
                    "2. Which facts are most critical for verification (e.g., dates, locations, events)?"
                ),
                "example_reasoning": (
                    "Target claim: 'Albert Einstein was born in Germany.' \n"
                    "Passages: \n"
                    "  [1] Einstein was born in Ulm, in the Kingdom of Württemberg in the German Empire.\n"
                    "  [2] He later moved to Switzerland.\n"
                    "Relevant fact: born in Ulm, Germany. \n"
                    "Summary: Albert Einstein was born in Ulm, Germany."
                ),
                "dependencies": [4],
            },
            # Step 6: Integrate evidence and conditionally generate third-hop query
            {
                "number": 6,
                "title": "Integrate evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Combine evidence from both hops and determine if third hop is needed.",
                "stage_action": (
                    "Integrate first-hop and second-hop summaries. \n"
                    "If combined evidence fully verifies the claim, output 'NO_QUERY_NEEDED'. \n"
                    "Otherwise, identify missing fact and write concise search query. \n"
                    "Provide ONLY the query or 'NO_QUERY_NEEDED', no additional text."
                ),
                "reasoning_questions": (
                    "1. What does combined evidence say about the claim?\n"
                    "2. Is any specific fact still missing for verification?\n"
                    "3. If missing, what is the most precise query to retrieve it?"
                ),
                "example_reasoning": (
                    "Case 1 (sufficient evidence):\n"
                    "Claim: 'Albert Einstein was born in Germany.' \n"
                    "First-hop summary: Albert Einstein was a theoretical physicist. \n"
                    "Second-hop summary: He was born in Ulm, Germany. \n"
                    "Combined: Claim verified. Output: NO_QUERY_NEEDED\n\n"
                    "Case 2 (insufficient evidence):\n"
                    "Claim: 'Albert Einstein was born in Germany.' \n"
                    "First-hop summary: Albert Einstein was a theoretical physicist. \n"
                    "Second-hop summary: He was born in the German Empire. \n"
                    "Missing: specific city (Ulm). Output: Albert Einstein birthplace city"
                ),
                "dependencies": [2, 5],
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