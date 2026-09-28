def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims. Your goal is to maximize retrieval coverage by ensuring all necessary evidence is found across three hops. Focus on identifying gaps and generating precise queries for each hop.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant to verifying the claim. "
                    "Summarize the most important evidence found. If no relevant facts are found, suggest a "
                    "rephrased version of the claim for better retrieval."
                ),
                "reasoning_questions": (
                    "What key entities and relationships are mentioned in the claim? "
                    "What evidence from the passages supports or contradicts the claim? "
                    "If no relevant facts are found, what rephrased claim might yield better results?"
                ),
                "example_reasoning": "<none>",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.' Missing: Construction date confirmation. Query: 'Eiffel Tower construction year'"
                ),
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Reconcile evidence from both hops, resolve contradictions, and identify remaining gaps for third-hop query generation.",
                "stage_action": (
                    "Reconcile the first-hop evidence summary and second-hop passages, resolving any contradictions. "
                    "Identify any remaining gaps in evidence needed to verify the claim. "
                    "Produce a unified evidence summary covering all relevant facts found so far."
                ),
                "reasoning_questions": (
                    "What entities and relationships are covered by the combined evidence? "
                    "Are there any contradictions between the first-hop and second-hop evidence? "
                    "What evidence is still missing for full verification?"
                ),
                "example_reasoning": "<none>",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a broad search query for the third hop to maximize coverage.",
                "stage_action": (
                    "Based on all evidence gathered so far, identify any remaining gaps and generate a broad search query "
                    "to capture diverse evidence for the third hop (which uses a deeper search with k=10). "
                    "Write a concise but comprehensive query.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.' Gaps: Construction date confirmation and context. Query: 'Eiffel Tower construction date year history'"
                ),
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
