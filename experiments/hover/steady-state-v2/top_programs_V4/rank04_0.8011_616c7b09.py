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
            # Step 1: First-hop retrieval (upgraded to deep)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence with gap focus
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly relate to verifying the claim. "
                    "Summarize the evidence concisely."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified based on the current evidence?",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query with clean example
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
                "example_reasoning": "Example: For claim 'Einstein was born in Germany', if evidence mentions Ulm, output: 'Einstein birthplace'",
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
            # Step 5: Summarize second-hop evidence with gap focus
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly relate to verifying the claim. "
                    "Summarize the evidence concisely."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified based on the current evidence?",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query with clean example
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
                "example_reasoning": "Example: For claim 'Marie Curie won two Nobel Prizes', if evidence shows Physics prize but not Chemistry, output: 'Marie Curie Nobel Prize Chemistry'",
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
            # Step 8: Summarize third-hop evidence with gap focus
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly relate to verifying the claim. "
                    "Summarize the evidence concisely."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified based on the current evidence?",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            # Step 9: Unconditional fourth-hop query generation (removed STOP)
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify missing evidence to retrieve additional supporting documents using all available evidence.",
                "stage_action": (
                    "Review all evidence summaries (first, second, and third hops) and the original claim. "
                    "Identify the exact missing information that would help retrieve more supporting documents for the claim. "
                    "Output a concise search query for that missing information. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: For claim 'The Eiffel Tower was built in 1889', if evidence confirms construction year but lacks architect details, output: 'Eiffel Tower architect'",
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