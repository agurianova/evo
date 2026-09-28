def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to retrieve evidence to verify a claim through multi-hop reasoning. Always output search queries EXACTLY as requested with no additional text, explanations, or formatting. When filtering passages, be rigorous and focus ONLY on facts directly relevant to verifying the claim's specific elements.",
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
            # Step 2: Filter first-hop passages (enhanced with borderline examples)
            {
                "number": 2,
                "title": "Filter claim-relevant first-hop passages",
                "step_type": "llm",
                "aim": "Identify and select passages containing facts directly verifiable against the claim.",
                "stage_action": (
                    "Review retrieved passages and output ONLY those providing facts that can confirm or refute specific claim elements. "
                    "Remove passages that mention claim entities but lack verification-critical details. "
                    "Preserve original passage format [i] Title | text."
                ),
                "reasoning_questions": (
                    "Which passages explicitly state facts matching claim elements (e.g., dates, relationships)? "
                    "Which passages mention claim entities but are missing verification-critical details (e.g., 'Eiffel Tower | construction began' without completion year for 'completed in 1889')? "
                    "Which passages are completely irrelevant?"
                ),
                "example_reasoning": (
                    "Example: Claim 'The Eiffel Tower was completed in 1889.' Retrieved passages: "
                    "[0] Paris | ... [1] Eiffel Tower | Construction began in 1887. [2] Eiffel Tower | Completed on March 15, 1889. "
                    "Relevant: [2] (states completion date). Irrelevant: [1] (mentions construction start but not completion)."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (enhanced gap analysis)
            {
                "number": 3,
                "title": "Generate precise second-hop query",
                "step_type": "llm",
                "aim": "Identify the single most critical missing verification element and generate a targeted search query.",
                "stage_action": (
                    "Based on filtered passages, list verified claim elements and identify the MOST critical missing fact. "
                    "Write ONLY the search query to find this specific evidence with no additional text."
                ),
                "reasoning_questions": (
                    "What claim elements are ALREADY VERIFIED by filtered passages? "
                    "What SINGLE SPECIFIC FACT is still missing that would confirm/refute the claim? "
                    "How can we phrase a query targeting ONLY this missing detail using precise entities/dates?"
                ),
                "example_reasoning": (
                    "Example: Claim 'Marie Curie won two Nobel Prizes in different sciences.' "
                    "Verified: Won Nobel Prizes. Missing: Specific sciences and years. "
                    "Query: 'Marie Curie Nobel Prize categories and years'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: NEW - Filter second-hop passages (critical fix for harmful pattern)
            {
                "number": 5,
                "title": "Filter claim-relevant second-hop passages",
                "step_type": "llm",
                "aim": "Isolate passages containing facts that directly address the missing verification element.",
                "stage_action": (
                    "Review second-hop passages and output ONLY those providing the specific missing fact identified in query generation. "
                    "Remove passages that discuss related topics but omit the critical detail. "
                    "Preserve original passage format [i] Title | text."
                ),
                "reasoning_questions": (
                    "Which passages explicitly state the missing fact from the query (e.g., specific year/category)? "
                    "Which passages mention related concepts but lack the critical detail (e.g., 'Nobel Prize' without category/year)? "
                    "Which passages are irrelevant to the specific gap?"
                ),
                "example_reasoning": (
                    "Example: Query 'Marie Curie Nobel Prize categories and years'. Retrieved passages: "
                    "[0] Nobel Prize | ... [1] Marie Curie | Awarded Physics prize in 1903 and Chemistry in 1911. [2] Nobel winners | ... "
                    "Relevant: [1] (specifies categories/years). Irrelevant: [0] (general Nobel info without Curie details)."
                ),
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (enhanced with multi-hop context)
            {
                "number": 6,
                "title": "Generate precise third-hop query",
                "step_type": "llm",
                "aim": "Identify the final verification gap using all filtered evidence and generate a targeted query.",
                "stage_action": (
                    "Based on ALL filtered evidence (first and second hop), list verified elements and the SINGLE most critical missing fact. "
                    "Write ONLY the search query to find this evidence with no additional text."
                ),
                "reasoning_questions": (
                    "What claim elements are NOW VERIFIED after reviewing both filtered hops? "
                    "What SPECIFIC DETAIL is still missing that would fully confirm/refute the claim? "
                    "How can we phrase a query incorporating context from multiple hops (e.g., 'Eiffel Tower completion verification source')?"
                ),
                "example_reasoning": (
                    "Example: Claim 'Moon landing occurred in 1969.' Verified: Apollo 11 mission (1969). Missing: Official NASA confirmation. "
                    "Query: 'NASA official Moon landing confirmation date 1969'"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }