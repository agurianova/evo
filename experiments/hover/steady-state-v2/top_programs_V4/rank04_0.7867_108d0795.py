def entrypoint():
    return {
        "system_prompt": "You are an expert in evidence gathering for claim verification. Your task is to ensure comprehensive coverage by identifying all necessary evidence through multi-hop retrieval. Always check for missing information and generate precise queries to fill gaps.",
        "steps": [
            # Step 1: First-hop retrieval with higher recall
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
            # Step 3: Generate second-hop query with examples
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
                    "Example: Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "First-hop summary: The Eiffel Tower is located in Paris and was built for the 1889 World's Fair.\n"
                    "Missing information: Where was it originally intended to be built?\n"
                    "Query: 'Eiffel Tower originally intended location'\n"
                    "Note: The query is concise and directly addresses the missing information."
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval with higher recall
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
            # Step 5: Summarize second-hop evidence (new step)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all second-hop retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Integrate first and second hop evidence
            {
                "number": 6,
                "title": "Integrate first and second hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary with the second-hop evidence summary. "
                    "Produce a unified evidence summary covering all relevant facts found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query with examples
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the unified evidence summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "Unified summary: The Eiffel Tower was built in Paris for the 1889 World's Fair. It was designed by Gustave Eiffel. \n"
                    "Missing information: Was Barcelona ever considered as a location?\n"
                    "Query: 'Eiffel Tower Barcelona proposal'\n"
                    "Note: The query targets the specific missing piece of evidence."
                ),
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval
            {
                "number": 8,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Gap analysis and fourth-hop query generation
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query generation",
                "step_type": "llm",
                "aim": "Analyze evidence sufficiency and generate a fourth-hop query if gaps remain.",
                "stage_action": (
                    "Based on the unified evidence summary (from step6) and the third-hop retrieved passages (from step8), "
                    "determine if there are any remaining gaps in evidence needed to verify the claim. "
                    "If gaps exist, write a concise search query to find the missing evidence. "
                    "If no gaps remain, output 'NO_MORE_HOPS'.\n"
                    "Provide ONLY the query or 'NO_MORE_HOPS', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "Unified summary: The Eiffel Tower was built in Paris for the 1889 World's Fair. It was designed by Gustave Eiffel. Some sources mention that the design was initially proposed for Barcelona but rejected.\n"
                    "Third-hop passages: [1] Title | ... Barcelona rejected the proposal ...\n"
                    "Analysis: The third-hop passage confirms Barcelona rejected the proposal, so the claim is false. No more evidence needed.\n"
                    "Output: NO_MORE_HOPS"
                ),
                "dependencies": [6, 8],
            },
            # Step 10: Fourth-hop retrieval (conditional)
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