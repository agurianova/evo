def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop evidence retrieval for claim verification. Always output search queries concisely and without extra text. When summarizing evidence, be precise and extract only relevant facts. When generating search queries, use specific entities and key phrases from the evidence to improve retrieval precision.",
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
            # Step 3: Generate second-hop query (enhanced context)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary (step2), determine what additional evidence is needed to "
                    "fully verify the claim. You may refer to the raw passages (step1) for nuanced details, but prioritize the summary. "
                    "Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop evidence: Construction of the Eiffel Tower began in January 1887.\n"
                    "Missing: The exact completion date.\n"
                    "Eiffel Tower completion date"
                ),
                "dependencies": [1, 2],
            },
            # Step 4: Second-hop retrieval (deeper search)
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
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Combine evidence (enhanced integration)
            {
                "number": 6,
                "title": "Combine evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (step2) with the second-hop evidence summary (step5). "
                    "Explicitly link facts between hops (e.g., 'This fact from hop1 supports/contradicts that fact from hop2'). "
                    "Produce a unified evidence summary covering all relevant facts found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query (hop-specific)
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the combined evidence summary (step6), determine what final piece "
                    "of evidence is needed to fully verify the claim. Note: This is the third hop, so focus on very specific, "
                    "granular details that might have been missed in the first two hops. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "Combined evidence: The Eiffel Tower's height is 300 meters without antennas.\n"
                    "Missing: Whether the standard height measurement includes antennas.\n"
                    "Eiffel Tower standard height measurement"
                ),
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval (deeper search)
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
            # Step 9: Gap analysis (fixed input consistency)
            {
                "number": 9,
                "title": "Gap analysis",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient and generate fourth-hop query if needed.",
                "stage_action": (
                    "First, create a concise summary of the third-hop retrieved passages (step8). Then, review the combined evidence "
                    "from first two hops (step6) and the third-hop summary. If the claim can be verified as true or false, output 'NO_QUERY'. "
                    "Otherwise, identify missing information and write a concise search query.\n"
                    "Provide ONLY the search query or 'NO_QUERY', no additional text."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. What evidence do we have from the first two hops (step6)?\n"
                    "3. What new evidence did we get in the third hop (step8)?\n"
                    "4. Is there any contradiction or gap in the evidence?\n"
                    "5. What specific piece of information is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Case 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Combined evidence: Construction began in 1887 and ended in 1889.\n"
                    "Third-hop evidence: Completion date is March 31, 1889.\n"
                    "Analysis: The claim is false because 'built in 1887' implies completion in 1887, but it was completed in 1889.\n"
                    "NO_QUERY\n\n"
                    "Case 2:\n"
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "Combined evidence: Height is 300 meters without antennas.\n"
                    "Third-hop evidence: Antennas add 24 meters.\n"
                    "Analysis: The claim does not specify if it includes antennas. We need the standard measurement.\n"
                    "Eiffel Tower standard height measurement"
                ),
                "dependencies": [6, 8],
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