def entrypoint():
    return {
        "system_prompt": (
            "You are an evidence verifier. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia abstracts. "
            "Success means finding all supporting documents for the claim. At each step, focus on extracting precise facts and identifying gaps."
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
                    "IMPORTANT: Output ONLY the search query string. Do not include any other text, explanations, or formatting."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Step2 output: The Eiffel Tower was built in Paris. There is evidence that Barcelona was considered but rejected.\n\n"
                    "Analysis: The claim states the tower was intended for Barcelona. The evidence confirms Barcelona was considered but rejected. "
                    "We need to know why it was rejected in Barcelona.\n"
                    "Missing: Reasons for rejection in Barcelona.\n"
                    "Query: 'Barcelona reject Eiffel Tower proposal reasons'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (using deep retrieval for higher recall)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Integrate evidence and identify gaps (using raw passages)
            {
                "number": 5,
                "title": "Integrate evidence and identify gaps",
                "step_type": "llm",
                "aim": "Combine evidence from all hops and identify remaining gaps.",
                "stage_action": (
                    "Review the raw passages from the first hop (step1) and the second hop (step4). "
                    "Produce a comprehensive evidence summary. Then, list any missing evidence required to fully verify the claim. "
                    "If no evidence is missing, state 'NO_GAPS'.\n"
                    "Output format: \n"
                    "## Evidence Summary\n"
                    "[summary text]\n"
                    "## Missing Evidence\n"
                    "[list of missing evidence or 'NO_GAPS']"
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the evidence integration output, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "IMPORTANT: Output ONLY the search query string. Do not include any other text, explanations, or formatting."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Step5 output:\n"
                    "## Evidence Summary\n"
                    "The Eiffel Tower was built in Paris. Historical records show that the proposal was initially considered by Barcelona but rejected.\n"
                    "## Missing Evidence\n"
                    "The specific reasons for Barcelona's rejection of the Eiffel Tower proposal.\n\n"
                    "Analysis: The missing evidence is the specific reasons. We need to find what those reasons were.\n"
                    "Query: 'Barcelona reject Eiffel Tower proposal specific reasons'"
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
