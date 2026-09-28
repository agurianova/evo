def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier for multi-hop claims. Always prioritize recall over precision. Your goal is to find as many relevant supporting documents as possible. When generating search queries, focus on missing information and use broad, recall-focused queries with synonyms and OR operators.",
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
            # Step 3: Generate second-hop query with recall-focused scaffolding
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information after first hop and generate a broad search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, determine what specific fact is missing to "
                    "verify the claim. Write a broad, recall-focused search query to find this missing information, "
                    "using synonyms and OR operators as needed.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities or relationships need further exploration with broad terminology?",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1887.' Evidence: 'The Eiffel Tower was completed in 1889.' Missing: exact construction start date. Query: 'Eiffel Tower construction start year OR Eiffel Tower began building date'",
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
            # Step 5: Combine first and second hop evidence with internal summarization
            {
                "number": 5,
                "title": "Combine first and second hop evidence",
                "step_type": "llm",
                "aim": "Integrate evidence from first and second hops into a unified summary through internal synthesis.",
                "stage_action": (
                    "Read the first-hop evidence summary (from step2) and the raw second-hop passages (from step4). "
                    "First, create a concise summary of the second-hop passages, ignoring the [i] numbering. "
                    "Then, integrate the first-hop summary and the second-hop summary into a unified two-hop evidence summary. "
                    "Identify connections between the hops and any remaining gaps."
                ),
                "reasoning_questions": "What are the key facts from the second-hop passages? What connections exist between the first-hop and second-hop evidence? What specific information is still missing to verify the claim?",
                "example_reasoning": "First-hop summary: 'The Eiffel Tower was completed in 1889.' Second-hop passages: [1] Eiffel Tower | Construction began in 1887. [2] Gustave Eiffel | Designed the Eiffel Tower in 1884. Summary of second hop: Construction of the Eiffel Tower began in 1887. Unified summary: The Eiffel Tower was designed by Gustave Eiffel in 1884, construction began in 1887, and it was completed in 1889. Missing: exact date construction began (month/day).",
                "dependencies": [2, 4],
            },
            # Step 6: Generate third-hop query with recall-focused scaffolding
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after two hops and generate a broad search query for the third hop.",
                "stage_action": (
                    "Based on the two-hop evidence summary (from step5), determine what specific fact is still missing to "
                    "verify the claim. Write a broad, recall-focused search query to find this missing information, "
                    "using synonyms and OR operators as needed.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What critical fact is still missing? Which entity or relationship has not been sufficiently verified with broad terminology?",
                "example_reasoning": "Claim: 'Marie Curie won two Nobel Prizes.' Combined evidence: 'Marie Curie won the Nobel Prize in Physics in 1903 and shared it with Pierre Curie and Henri Becquerel.' Missing: the second Nobel Prize (in Chemistry, 1911). Query: 'Marie Curie second Nobel Prize year OR Marie Curie Chemistry Nobel'",
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval with deep recall
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Generate fourth-hop query with adaptive termination
            {
                "number": 8,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after three hops and generate adaptive search query for fourth hop.",
                "stage_action": (
                    "Read the two-hop evidence summary (from step5) and the raw third-hop passages (from step7). "
                    "First, create a concise summary of the third-hop passages, ignoring the [i] numbering. "
                    "Then, integrate all evidence into a unified three-hop evidence summary. "
                    "If the claim is fully verified by this evidence, output 'NO_HOP'. "
                    "Otherwise, determine what critical fact is still missing and write a broad, recall-focused search query to find this missing evidence, "
                    "using synonyms and OR operators as needed.\n"
                    "Provide ONLY the search query or 'NO_HOP', no additional text."
                ),
                "reasoning_questions": "What are the key facts from the third-hop passages? How do they connect to the two-hop summary? Is the claim fully verified? If not, what specific information is still missing with broad terminology?",
                "example_reasoning": "Two-hop summary: 'The Eiffel Tower was designed by Gustave Eiffel in 1884, construction began in 1887, and it was completed in 1889.' Third-hop passages: [1] Eiffel Tower | Construction started on January 28, 1887. [2] Paris | The Eiffel Tower was built for the 1889 World's Fair. Summary of third hop: Construction of the Eiffel Tower started on January 28, 1887. Unified summary: The Eiffel Tower was designed by Gustave Eiffel in 1884, construction began on January 28, 1887, and it was completed in 1889. The claim is fully verified. Output: NO_HOP",
                "dependencies": [5, 7],
            },
            # Step 9: Fourth-hop retrieval with deep recall (adaptive)
            {
                "number": 9,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
        ],
    }