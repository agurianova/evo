def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier for claim verification. Your goal is to retrieve all relevant Wikipedia passages that support or refute the claim. Success is measured by the completeness of the retrieved evidence. Always focus on the most direct and relevant evidence. When generating search queries, output ONLY the query string with no additional text.",
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
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example:\n"
                    'Query: "who invented the telephone"\n\n'
                    "Do not add any other text."
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
            # Step 5: Analyze evidence and identify gaps (changed from parent)
            {
                "number": 5,
                "title": "Analyze evidence and identify gaps",
                "step_type": "llm",
                "aim": "Assess the completeness of evidence from the first two hops and explicitly list missing information.",
                "stage_action": (
                    "Review the raw passages from the first hop (step1) and second hop (step4). "
                    "Produce a comprehensive summary of the evidence found. Then, explicitly list the missing pieces "
                    "of evidence required to verify the claim. Be specific about what facts are still needed."
                ),
                "reasoning_questions": (
                    "1. What key facts about the claim have been confirmed by the retrieved passages?\n"
                    "2. What specific information is still missing to fully verify the claim?"
                ),
                "example_reasoning": (
                    "From the first hop, we found that [fact1] and [fact2]. From the second hop, we found [fact3]. "
                    "However, the claim requires evidence about [missing fact]. We still need to verify [another missing fact]."
                ),
                "dependencies": [1, 4],
            },
            # Step 6: Generate next-hop query or terminate (replaces parent's step6)
            {
                "number": 6,
                "title": "Generate next-hop query or terminate",
                "step_type": "llm",
                "aim": "Determine if a third hop is necessary and generate a search query if so.",
                "stage_action": (
                    "Based on the gap analysis from step5, if there are missing pieces of evidence, generate a concise "
                    "search query to find them. If no more evidence is needed, output exactly 'NO_MORE_HOPS'.\n"
                    "Provide ONLY the query string or 'NO_MORE_HOPS', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example 1 (gaps exist):\n"
                    'Query: "what was the cause of the 1929 stock market crash"\n\n'
                    "Example 2 (no gaps):\n"
                    "NO_MORE_HOPS"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval (deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }
