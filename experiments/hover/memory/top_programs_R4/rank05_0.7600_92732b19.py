def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Your task is to verify claims by retrieving relevant Wikipedia passages through multi-hop reasoning. After each retrieval, summarize key facts directly relevant to the claim, identify evidence gaps, and generate precise search queries for the next hop. Prioritize factual accuracy and relevance to the claim.",
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
            # Step 2: Summarize first-hop evidence with enhanced scaffolding
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "What specific facts directly support or refute the claim? "
                    "Which details are ambiguous or insufficient for verification? "
                    "What concrete information is still missing?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.' "
                    "Passages state it was 'built as the entrance arch for the 1889 World's Fair and scheduled for dismantling in 1909.' "
                    "This supports the temporary nature but doesn't address 'original intent' - we need evidence about designers' initial plans."
                ),
                "dependencies": [1],
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
                "example_reasoning": "<none>",
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
            # Step 5: Summarize evidence with raw passage access
            {
                "number": 5,
                "title": "Summarize integrated evidence",
                "step_type": "llm",
                "aim": "Combine all evidence into a comprehensive verification-focused summary.",
                "stage_action": (
                    "Integrate passages from both hops. Highlight facts that directly support/refute the claim, "
                    "resolve contradictions, and identify any remaining verification gaps."
                ),
                "reasoning_questions": (
                    "How do the two sets of passages interact - do they corroborate or conflict? "
                    "What is now verifiable that wasn't with first hop alone? "
                    "What single piece of evidence would conclusively verify the claim?"
                ),
                "example_reasoning": (
                    "First hop showed Eiffel Tower's scheduled dismantling date (1909). "
                    "Second hop reveals Gustave Eiffel's 1887 contract stating 'temporary exposition structure'. "
                    "Together they confirm original temporary intent - no further evidence needed."
                ),
                "dependencies": [1, 4],  # Changed from [2,4] to access raw passages
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [5],
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