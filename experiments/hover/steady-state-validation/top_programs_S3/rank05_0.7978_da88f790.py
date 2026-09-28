def entrypoint():
    return {
        "system_prompt": "",
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
            # Step 5: Summarize evidence from first two hops (using raw passages)
            {
                "number": 5,
                "title": "Summarize first and second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence (raw passages) with the second-hop evidence (raw passages). "
                    "Produce a unified evidence summary covering all relevant facts found so far."
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
                    "Based on all evidence gathered so far, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
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
            # Step 8: Gap analysis after third hop
            {
                "number": 8,
                "title": "Analyze evidence gaps after third hop",
                "step_type": "llm",
                "aim": "Identify remaining gaps in evidence after three retrieval hops.",
                "stage_action": (
                    "Review all evidence gathered so far (from the first two hops summary and the third-hop passages). "
                    "Determine what specific facts are still missing to verify the claim."
                ),
                "reasoning_questions": "What specific facts are still missing? Which parts of the claim remain unverified? What entities or relationships need further evidence?",
                "example_reasoning": "The claim states that X caused Y. We have evidence that X occurred and that Y occurred, but we lack evidence of a causal link between X and Y. Therefore, we need to find evidence that X directly caused Y.",
                "dependencies": [5, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Formulate a precise search query to retrieve the missing evidence identified in the gap analysis.",
                "stage_action": (
                    "Based on the gap analysis, write a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities or relationships should the query target? How can the query be made precise to avoid irrelevant results?",
                "example_reasoning": "Missing fact: causal link between X and Y. Query: 'X caused Y' OR 'X effect on Y'",
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
