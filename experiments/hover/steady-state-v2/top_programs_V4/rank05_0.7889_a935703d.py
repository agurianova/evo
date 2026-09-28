def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Your goal is to gather as much relevant evidence as possible from Wikipedia to verify the claim. Always prioritize completeness of evidence over brevity. When generating search queries, focus on missing information that would help verify the claim.",
        "steps": [
            # Step 1: First-hop retrieval (deep)
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
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
                "example_reasoning": (
                    "Example: For the claim 'The Eiffel Tower was built in 1889', the retrieved passages mention: "
                    "[1] Paris | The Eiffel Tower was completed in 1889. "
                    "[2] Gustave Eiffel | Designed the tower for the 1889 World's Fair. "
                    "Key facts: The Eiffel Tower was built in 1889 and was designed by Gustave Eiffel for the World's Fair."
                ),
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
                    "evidence.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was built in 1889'. "
                    "First-hop summary: The Eiffel Tower was built in 1889 and designed by Gustave Eiffel. "
                    "Missing: Who was the chief engineer? Query: 'Eiffel Tower chief engineer'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep)
            {
                "number": 4,
                "title": "Retrieve second-hop passages (deep)",
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
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all second-hop retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: For the claim 'The Eiffel Tower was built in 1889', second-hop passages: "
                    "[1] Maurice Koechlin | Chief engineer of the Eiffel Tower. "
                    "[2] Émile Nouguier | Co-engineer of the Eiffel Tower. "
                    "Key facts: Maurice Koechlin was the chief engineer and Émile Nouguier was a co-engineer."
                ),
                "dependencies": [4],
            },
            # Step 6: Integrate first and second hop evidence
            {
                "number": 6,
                "title": "Integrate first and second hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (step2) with the second-hop evidence summary (step5). "
                    "Produce a unified evidence summary covering all relevant facts found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the integrated evidence summary (step6), determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was built in 1889'. "
                    "Current evidence: Built in 1889, designed by Gustave Eiffel, chief engineer Maurice Koechlin. "
                    "Missing: Was it the tallest structure at the time? Query: 'Eiffel Tower tallest structure 1889'"
                ),
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval (deep)
            {
                "number": 8,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Analyze evidence gaps and generate fourth-hop query
            {
                "number": 9,
                "title": "Analyze evidence gaps and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if there is missing evidence to fully verify the claim and generate a query for the fourth hop if needed.",
                "stage_action": (
                    "You have the integrated evidence from the first two hops (step6) and the raw third-hop passages (step8). "
                    "First, integrate the third-hop passages with the existing evidence to form a complete summary. "
                    "Then, determine if there are still gaps in the evidence that would help verify the claim. "
                    "If gaps exist, write a concise search query to find the missing evidence. "
                    "If no gaps remain, write 'NO_QUERY_NEEDED'. "
                    "Provide ONLY the search query or 'NO_QUERY_NEEDED', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example: Claim: 'The Eiffel Tower was built in 1889'. "
                    "Step6 (integrated first and second hop): Built in 1889, designed by Gustave Eiffel, chief engineer Maurice Koechlin. "
                    "Step8 (third-hop passages): [1] Tallest structure | The Eiffel Tower was the tallest man-made structure until 1930. "
                    "Complete summary: Built in 1889, designed by Gustave Eiffel, chief engineer Maurice Koechlin, and was the tallest structure until 1930. "
                    "Missing: How many workers died during construction? Query: 'Eiffel Tower construction worker deaths'"
                ),
                "dependencies": [6, 8],
            },
            # Step 10: Fourth-hop retrieval (deep)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }