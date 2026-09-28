def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims using multi-hop evidence retrieval. Your goal is to maximize retrieval coverage by ensuring all necessary evidence is found. Be precise, thorough, and focus on identifying gaps for the next search.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim and handle cases with no relevant evidence.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to the claim. "
                    "If relevant facts are found, summarize the key evidence. "
                    "If no relevant facts are found, suggest a rephrased claim that might yield better search results."
                ),
                "reasoning_questions": (
                    "1. What are the key entities and relationships in the claim?\n"
                    "2. Which facts in the retrieved passages are directly relevant to the claim?\n"
                    "3. If no relevant facts are found, how should the claim be rephrased for better retrieval?"
                ),
                "example_reasoning": "<none>",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a focused search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The Eiffel Tower was originally intended to be built in Barcelona.\n"
                    "Evidence summary: The Eiffel Tower was built in Paris for the 1889 World's Fair by Gustave Eiffel's company.\n"
                    "Missing: The evidence does not mention Barcelona. We need to find out if there was a plan to build the tower in Barcelona.\n"
                    "Eiffel Tower original intended location Barcelona"
                ),
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Combine and reconcile evidence from both hops into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary with the second-hop passages. "
                    "Reconcile any conflicting information and resolve contradictions. "
                    "Produce a unified evidence summary that covers all relevant facts found so far and identifies any remaining gaps."
                ),
                "reasoning_questions": (
                    "1. Are there any contradictions between the first-hop and second-hop evidence?\n"
                    "2. How can conflicting information be resolved?\n"
                    "3. What specific information is still missing to fully verify the claim?"
                ),
                "example_reasoning": "<none>",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a broad search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise but "
                    "broad search query to find this evidence (since we are using a deeper search).\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: The Eiffel Tower was originally intended to be built in Barcelona.\n"
                    "Current evidence: The Eiffel Tower was built in Paris. Some sources mention a proposal for Barcelona but it was rejected.\n"
                    "Missing: We need to confirm the details of the Barcelona proposal and why it was rejected.\n"
                    "Eiffel Tower Barcelona proposal history reasons for rejection"
                ),
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
