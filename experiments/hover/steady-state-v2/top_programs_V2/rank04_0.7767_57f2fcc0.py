def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your task is to verify claims by retrieving and analyzing evidence from Wikipedia. Be precise and thorough in identifying gaps and generating search queries.",
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
                    "Gap: First-hop shows Paris is the capital of France, but does not mention when it became the capital. "
                    "Query: 'When did Paris become the capital of France'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (using deep for narrow query)
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
            # Step 5: Summarize first and second hop with gap analysis
            {
                "number": 5,
                "title": "Summarize evidence and identify gaps",
                "step_type": "llm",
                "aim": "Integrate first-hop and second-hop evidence and identify specific gaps for the next hop.",
                "stage_action": (
                    "Combine the evidence summary from the first hop with the second-hop passages. "
                    "Produce a unified summary and explicitly state what information is still missing to verify the claim."
                ),
                "reasoning_questions": (
                    "What parts of the claim have been verified by the evidence so far? "
                    "What specific facts are still unverified? "
                    "What additional information would help verify the claim?"
                ),
                "example_reasoning": (
                    "The claim: 'The Eiffel Tower was built in 1887.' "
                    "First-hop: Confirms the Eiffel Tower exists in Paris. "
                    "Second-hop: Shows construction started in 1887. "
                    "Gap: We have start date but not completion date. Missing: Exact year of completion."
                ),
                "dependencies": [2, 4],
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
                "example_reasoning": (
                    "Gap: Second-hop shows Paris became capital in 508 AD, but claim states 508 AD specifically. Need confirmation of exact date. "
                    "Query: 'Paris capital of France 508 AD confirmation'"
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
            # Step 8: Summarize all evidence including third hop
            {
                "number": 8,
                "title": "Summarize all evidence and identify final gaps",
                "step_type": "llm",
                "aim": "Integrate all evidence gathered so far and identify specific gaps for final verification.",
                "stage_action": (
                    "Combine the evidence summary from the first two hops (step5) with the third-hop passages (step7). "
                    "Produce a unified evidence summary and explicitly state what specific information is still missing to fully verify the claim."
                ),
                "reasoning_questions": (
                    "What parts of the claim have been verified by the evidence so far? "
                    "What specific facts are still unverified? "
                    "What additional information would conclusively verify or refute the claim?"
                ),
                "example_reasoning": (
                    "The claim: 'The Eiffel Tower was built in 1887.' "
                    "First and second hop summary: Construction started in 1887. "
                    "Third-hop: Mentions completion in 1889. "
                    "Gap: We have start and completion, but not the specific year of construction (1887 vs 1889). "
                    "Missing: Exact year of construction completion or official inauguration."
                ),
                "dependencies": [5, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a precise search query to find the missing evidence identified in the gap analysis.",
                "stage_action": (
                    "Based on the gap analysis from step8, write a concise search query to retrieve the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Gap: Exact year of Eiffel Tower construction completion. "
                    "Query: 'Eiffel Tower construction completion year'"
                ),
                "dependencies": [8],
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