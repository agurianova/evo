def entrypoint():
    return {
        "system_prompt": (
            "You are an expert fact-checker assistant. Your task is to verify claims by retrieving relevant evidence from Wikipedia. "
            "Follow these principles:\n"
            "- Always base your reasoning on the retrieved passages and the original claim.\n"
            "- For query generation steps, output ONLY the search query without any additional text.\n"
            "- For summarization steps, focus on extracting facts directly relevant to the claim.\n"
            "- In gap analysis, be thorough: if any part of the claim remains unverified, generate a query to find the missing evidence."
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
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly relate to verifying the claim. "
                    "Summarize the evidence concisely."
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
                "aim": "Identify the next logical piece of evidence to verify the claim based on the first-hop summary.",
                "stage_action": (
                    "Based on the summary of the first-hop evidence and the original claim, determine what specific information is still needed. "
                    "Formulate a concise search query to find that information. "
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
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly relate to verifying the claim. "
                    "Summarize the evidence concisely."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the precise missing piece of evidence needed to complete verification, using both first and second-hop summaries.",
                "stage_action": (
                    "Integrate the evidence from the first and second hops. Identify the exact gap that remains. "
                    "Formulate a highly specific search query to find the missing piece. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5],
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
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly relate to verifying the claim. "
                    "Summarize the evidence concisely."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            # Step 9: Gap analysis and fourth-hop query generation
            {
                "number": 9,
                "title": "Analyze evidence gaps and decide on fourth hop",
                "step_type": "llm",
                "aim": "Determine if the evidence from three hops is sufficient to verify the claim. If not, generate a query for the missing evidence.",
                "stage_action": (
                    "Review all evidence summaries (first, second, and third hops) and the original claim. "
                    "If the claim can be verified as true or false with the current evidence, output 'STOP'. "
                    "Otherwise, identify the exact missing information and output a concise search query for it. "
                    "Output ONLY 'STOP' or the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deeper search)
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