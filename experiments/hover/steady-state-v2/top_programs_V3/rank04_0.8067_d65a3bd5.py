def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier specializing in multi-hop claim verification. Your goal is to maximize retrieval coverage by ensuring all relevant evidence is found. When generating search queries, prioritize recall over precision to capture as many potentially relevant documents as possible.",
        "steps": [
            # Step 1: First-hop retrieval with deeper search
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
            # Step 3: Generate second-hop query with expert scaffolding
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
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "First-hop evidence: [1] Eiffel Tower | Built in Paris from 1887 to 1889. [2] Gustave Eiffel | French engineer.\n"
                    "Missing information: The source of the iron.\n"
                    "Generated query: 'Eiffel Tower iron source Lorraine region'"
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
            # Step 5: Summarize first and second hop evidence (FIXED DEPENDENCIES)
            {
                "number": 5,
                "title": "Summarize first and second hop evidence",
                "step_type": "llm",
                "aim": "Combine evidence from the first and second retrieval hops into a comprehensive summary.",
                "stage_action": (
                    "Integrate the raw passages from the first-hop (step1) and second-hop (step4) retrievals. "
                    "Extract all facts relevant to verifying the claim and produce a unified summary "
                    "covering both hops."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],  # FIXED: now uses raw passages instead of summaries
            },
            # Step 6: Generate third-hop query with expert scaffolding
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
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Evidence so far: First-hop: Eiffel Tower built 1887-1889. Second-hop: [1] Lorraine | Region in France known for iron ore.\n"
                    "Missing information: Direct connection between Eiffel Tower construction and Lorraine iron.\n"
                    "Generated query: 'Eiffel Tower construction iron supplier Lorraine'"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval with deeper search
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
            # Step 8: Summarize first, second, and third hop evidence
            {
                "number": 8,
                "title": "Summarize first, second, and third hop evidence",
                "step_type": "llm",
                "aim": "Combine evidence from all three retrieval hops into a comprehensive summary.",
                "stage_action": (
                    "Integrate the raw passages from the first-hop (step1), second-hop (step4), "
                    "and third-hop (step7) retrievals. Extract all facts relevant to verifying "
                    "the claim and produce a unified summary covering all three hops."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4, 7],
            },
            # Step 9: Generate fourth-hop query with expert scaffolding
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify any remaining evidence gaps and generate a search query for the fourth hop.",
                "stage_action": (
                    "Based on the complete evidence summary, determine if any critical information "
                    "is still missing to verify the claim. Write a concise search query to find "
                    "this final evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Evidence so far: ... (all previous evidence including third-hop)\n"
                    "Missing information: Documentation of the iron shipment from Lorraine to Paris.\n"
                    "Generated query: 'Eiffel Tower construction records iron shipment Lorraine'"
                ),
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval with deeper search
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