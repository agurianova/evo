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
            # Step 2: Summarize first-hop evidence with formatting instruction
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant to verifying the claim. "
                    "Summarize the most important evidence found. Ignore [i] numbering; focus only on passage content."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query with broad recall focus
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
                "reasoning_questions": "What specific fact is missing? Which entities or relationships need further exploration with alternative phrasing?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.' Evidence: 'The Eiffel Tower was completed in 1889.' "
                    "Missing: exact construction start date. Query: 'Eiffel Tower construction start year OR when construction began OR groundbreaking date'"
                ),
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
            # Step 5: NEW - Summarize second-hop evidence (addresses insight 1)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from second-hop passages relevant to the claim and first-hop evidence.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant to verifying the claim. "
                    "Summarize the most important evidence found. Ignore [i] numbering; focus only on passage content."
                ),
                "reasoning_questions": "What specific facts are provided? How do they connect to the first-hop evidence and claim?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.' First-hop evidence: 'The Eiffel Tower was completed in 1889.' "
                    "Second-hop passages: [1] Construction | The Eiffel Tower construction began in 1887. [2] History | Work started on the foundation in January 1887. "
                    "Key fact: construction started in 1887."
                ),
                "dependencies": [4],
            },
            # Step 6: Combine first and second hop evidence with scaffolding (addresses insight 3 & 5)
            {
                "number": 6,
                "title": "Combine first and second hop evidence",
                "step_type": "llm",
                "aim": "Integrate evidence from first and second hops into a unified summary.",
                "stage_action": (
                    "Using the first-hop summary (step2) and second-hop summary (step5), identify all relevant facts "
                    "supporting the claim verification. Produce a comprehensive evidence summary showing connections between hops."
                ),
                "reasoning_questions": "What connections exist between first-hop and second-hop evidence? How do they collectively support the claim?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.' First-hop summary: 'The Eiffel Tower was completed in 1889.' "
                    "Second-hop summary: 'Construction of the Eiffel Tower began in 1887.' Connection: The claim states 'built' in 1887, "
                    "which matches the construction start year. The evidence supports that construction commenced in 1887."
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query with broad recall focus
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after two hops and generate broad search query for third hop.",
                "stage_action": (
                    "Based on the combined evidence summary (step6), determine what final piece of evidence is needed to "
                    "fully verify the claim. Write a broad, recall-focused search query using synonyms/OR operators.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What critical fact is still missing? Which entity relationships need verification with alternative phrasing?",
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes.' Combined evidence: 'Marie Curie won the Nobel Prize in Physics in 1903.' "
                    "Missing: second prize details. Query: 'Marie Curie second Nobel Prize year OR field OR category'"
                ),
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
            # Step 9: Generate fourth-hop query with adaptive behavior (addresses insight 6)
            {
                "number": 9,
                "title": "Generate adaptive fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if fourth hop is needed and generate appropriate query.",
                "stage_action": (
                    "Based on the combined evidence from first two hops (step6) and third-hop passages (step8), determine if "
                    "additional evidence is still needed. If the claim is fully verified, output 'NO_HOP'. Otherwise, write a "
                    "broad, recall-focused search query using synonyms/OR operators.\nProvide ONLY 'NO_HOP' or the search query."
                ),
                "reasoning_questions": "Is the claim fully supported? If not, what specific information is missing with alternative phrasing?",
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919.' Combined evidence: 'The Treaty ended WWI.' "
                    "Third-hop passages: [1] Signing | Signed on June 28, 1919. Analysis: Signing date in 1919 is confirmed. "
                    "Output: NO_HOP\n\nClaim: 'Marie Curie won two Nobel Prizes.' Combined evidence: 'Won Physics prize in 1903.' "
                    "Third-hop passages: [1] Chemistry | Awarded second prize in Chemistry. Missing: year. Query: 'Marie Curie second Nobel Prize year'"
                ),
                "dependencies": [6, 8],
            },
            # Step 10: Fourth-hop retrieval (skips when query='NO_HOP')
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