def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant for claim verification. Your goal is to maximize the retrieval of supporting documents by conducting multi-hop searches. Always aim for comprehensive coverage: if evidence is insufficient, generate queries to fill gaps. Provide concise, focused outputs as instructed.",
        "steps": [
            # Step 1: First-hop retrieval (deep)
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
            # Step 3: Generate second-hop query (with example)
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
                    "Claim: 'The speed of light in vacuum is 299,792,458 m/s.'\n"
                    "First-hop evidence: 'Light travels at a finite speed. In vacuum, it is a fundamental constant of nature.'\n"
                    "Analysis: The evidence states light has a finite speed in vacuum but does not give the value. We need the exact value.\n"
                    "Query: 'speed of light in vacuum value'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep)
            {
                "number": 4,
                "title": "Retrieve second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly address the missing "
                    "information from the first hop. Produce a concise summary of the second-hop evidence."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (with example)
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
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The speed of light in vacuum is 299,792,458 m/s.'\n"
                    "Current evidence: 'The speed of light is approximately 300,000 km/s.'\n"
                    "Analysis: The evidence gives an approximation but we need the exact value as stated in the claim.\n"
                    "Query: 'exact speed of light in vacuum'"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval (deep)
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Integrated evidence summary (up to third hop)
            {
                "number": 8,
                "title": "Integrated evidence summary",
                "step_type": "llm",
                "aim": "Combine all evidence from first, second, and third hops into a comprehensive summary.",
                "stage_action": (
                    "Read the first-hop summary (step2), second-hop summary (step5), and third-hop passages (step7). "
                    "Produce a single, unified summary of all relevant facts found so far, focusing on the claim."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5, 7],
            },
            # Step 9: Gap analysis and fourth-hop query generation
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient; generate fourth-hop query if gaps exist.",
                "stage_action": (
                    "Based on the integrated evidence summary, check if all necessary facts are present to verify the claim. "
                    "If there is a gap, write a concise search query to find the missing evidence. "
                    "If the evidence is sufficient, output 'NO_GAP'.\n"
                    "Provide ONLY the query or 'NO_GAP', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval (if needed)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }