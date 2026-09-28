def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier for multi-hop claims. Always prioritize recall over precision. Your goal is to find as many relevant supporting documents as possible. When generating search queries, focus on missing information and use precise entity names.",
        "steps": [
            # Step 1: First-hop retrieval with deep recall
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
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query with recall focus
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information after first hop and generate a broad search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, determine what specific fact is missing to "
                    "verify the claim. Write a broad, recall-focused search query using synonyms/OR operators "
                    "to find this missing information.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities or relationships need further exploration?",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1887.' Evidence: 'The Eiffel Tower was completed in 1889.' Missing: exact construction start date. Query: 'Eiffel Tower construction start year OR began year'",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval with deep recall
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
            # Step 5: Summarize second-hop evidence (NEW)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Combine first and second hop evidence with scaffolding
            {
                "number": 6,
                "title": "Combine first and second hop evidence",
                "step_type": "llm",
                "aim": "Integrate evidence from first and second hops into a unified summary.",
                "stage_action": (
                    "Using the summary of the first-hop evidence (from step2) and the summary of the second-hop evidence (from step5), "
                    "identify all relevant facts supporting the claim verification. Produce a comprehensive evidence summary covering connections between hops. "
                    "Ignore [i] numbering in any passage references; focus only on the content."
                ),
                "reasoning_questions": "What connections exist between the first-hop and second-hop evidence? What specific fact is still missing to verify the claim?",
                "example_reasoning": "First-hop summary: 'The Eiffel Tower was completed in 1889.' Second-hop summary: 'Construction of the Eiffel Tower began in 1887.' Unified summary: 'The Eiffel Tower was built between 1887 and 1889.' Missing: the exact start date is 1887, but the claim might be about the start year.",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query with recall focus
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify missing information after two hops and generate a broad search query for the third hop.",
                "stage_action": (
                    "Based on the combined evidence from the first two hops (step6), determine what specific fact is missing to "
                    "verify the claim. Write a broad, recall-focused search query using synonyms/OR operators to find this missing information.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities or relationships need further exploration?",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1887.' Combined evidence: 'The Eiffel Tower was built between 1887 and 1889.' Missing: exact construction start date. Query: 'Eiffel Tower construction start year OR began year'",
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval with deep recall
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
            # Step 9: Generate fourth-hop query with adaptive hop
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if the claim is fully verified by current evidence. If not, generate broad query for fourth hop; else indicate no hop needed.",
                "stage_action": (
                    "Based on the combined evidence from the first two hops (step6) and the third-hop retrieved passages (step8), "
                    "check if the claim can be verified. If verified, output 'NO_HOP'. Otherwise, write a broad, recall-focused search query "
                    "using synonyms/OR operators to find the missing evidence.\n"
                    "Provide ONLY the query or 'NO_HOP', no additional text."
                ),
                "reasoning_questions": "What critical fact is still missing? Which entity or relationship has not been sufficiently verified?",
                "example_reasoning": "Claim: 'Marie Curie won two Nobel Prizes.' Combined evidence from first two hops: 'Marie Curie won the Nobel Prize in Physics in 1903.' Third-hop passages: 'Marie Curie was awarded the Nobel Prize in Chemistry in 1911.' Verified: YES. Output: 'NO_HOP'",
                "dependencies": [6, 8],
            },
            # Step 10: Fourth-hop retrieval with deep recall
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