def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier specializing in multi-hop claim verification. Your goal is to retrieve all supporting Wikipedia passages by generating precise search queries at each hop. Always focus on identifying missing evidence and formulating targeted queries. Success is measured by the completeness of retrieved evidence.",
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
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information after the first hop and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific evidence is missing? How can we formulate a query to retrieve it?",
                "example_reasoning": "The claim is about the causes of World War I. The first hop provided evidence about the assassination of Archduke Franz Ferdinand. We need evidence about the alliance systems. Query: 'alliance systems before World War I'",
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
            # Step 5: Assess evidence after two hops
            {
                "number": 5,
                "title": "Assess evidence after two hops",
                "step_type": "llm",
                "aim": "Determine if additional evidence is needed beyond the first two hops and generate a precise search query for the third hop if gaps exist.",
                "stage_action": (
                    "Review the raw passages from the first and second hops. If the claim can be verified with the current evidence, output 'NO_QUERY_NEEDED'. "
                    "Otherwise, output ONLY the search query for the missing evidence. Do not include any other text."
                ),
                "reasoning_questions": "What specific evidence is still missing to verify the claim? How can we formulate a concise query to find it?",
                "example_reasoning": "The claim states that X. From the first hop, we have evidence about A and B. From the second hop, we have evidence about C. However, we lack evidence about D, which is crucial. Therefore, the query should be: 'D proof'",
                "dependencies": [1, 4],
            },
            # Step 6: Third-hop retrieval (deeper search)
            {
                "number": 6,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [5],
            },
            # Step 7: Assess evidence after three hops
            {
                "number": 7,
                "title": "Assess evidence after three hops",
                "step_type": "llm",
                "aim": "Determine if additional evidence is needed beyond the first three hops and generate a precise search query for the fourth hop if gaps exist.",
                "stage_action": (
                    "Review the raw passages from all hops so far. If the claim can be verified, output 'NO_QUERY_NEEDED'. "
                    "Otherwise, output ONLY the search query for the missing evidence. Do not include any other text."
                ),
                "reasoning_questions": "What specific evidence is still missing to verify the claim? How can we formulate a concise query to find it?",
                "example_reasoning": "The claim states that X. We have evidence about A, B, C, and D from previous hops. However, we lack evidence about E. Therefore, the query should be: 'E verification'",
                "dependencies": [1, 4, 6],
            },
            # Step 8: Fourth-hop retrieval (deeper search)
            {
                "number": 8,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
        ],
    }
