def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Always prioritize recall for multi-hop claims. Verify claims by retrieving all relevant evidence. If evidence is insufficient, generate new queries to fill gaps.",
        "steps": [
            # Step 1: First-hop retrieval with deep recall
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
            # Step 2: Generate second-hop query with reasoning scaffolds
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Read the retrieved passages. Determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query for the missing evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to verify the claim? "
                    "What keywords would appear in a document containing that fact?"
                ),
                "example_reasoning": (
                    "The claim states 'The Eiffel Tower was built in 1887'. The retrieved passages mention the construction started in 1887 "
                    "but do not specify completion. To verify the claim, we need the completion date. Query: 'Eiffel Tower completion date'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate third-hop query with integrated evidence analysis
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Review all retrieved passages so far (first and second hop). Determine what evidence is still missing to verify the claim. "
                    "Write a concise search query for the missing evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Given the evidence from the first two hops, what specific fact is still missing? "
                    "What entities or events are central to the missing fact?"
                ),
                "example_reasoning": (
                    "The claim is about the Eiffel Tower's construction. First hop: construction started in 1887. "
                    "Second hop: it was built for the 1889 World's Fair. Missing: whether it was completed in 1887? "
                    "Actually, the claim says 'built in 1887' but construction started in 1887 and ended in 1889. "
                    "We need to confirm the completion year. Query: 'Eiffel Tower completion year'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate fourth-hop query with comprehensive integration
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify any remaining gaps and generate a search query for the fourth hop.",
                "stage_action": (
                    "Review all retrieved passages (first, second, and third hop). Determine if there is still missing evidence to verify the claim. "
                    "Write a concise search query for the missing evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "After three hops, what is the final piece of evidence needed? "
                    "What is the most specific query to get that evidence?"
                ),
                "example_reasoning": (
                    "The claim: 'The Eiffel Tower was built in 1887'. Evidence: started 1887, completed 1889. "
                    "The claim is false because it was completed in 1889. But we need to confirm the exact completion date. "
                    "Query: 'Eiffel Tower completion date'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval with deep recall
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }