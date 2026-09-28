def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to retrieve evidence to verify a claim through multi-hop reasoning. Always output search queries exactly as requested with no additional text. When filtering or summarizing, be rigorous and focus only on facts directly relevant to the claim.",
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
            # Step 2: Filter first-hop passages
            {
                "number": 2,
                "title": "Filter claim-relevant passages",
                "step_type": "llm",
                "aim": "Identify and select only passages directly relevant to verifying the claim.",
                "stage_action": (
                    "Review the retrieved passages and output ONLY those containing information pertinent to the claim. "
                    "Remove any passages that don't mention claim entities or provide directly relevant context. "
                    "Preserve the original passage format [i] Title | text."
                ),
                "reasoning_questions": (
                    "Which passages explicitly mention entities or facts in the claim? "
                    "Which passages provide necessary context for verification? "
                    "Which passages are completely irrelevant and should be discarded?"
                ),
                "example_reasoning": (
                    "Example: Claim 'The Eiffel Tower was completed in 1889.' Retrieved passages: "
                    "[0] Paris | ... [1] Eiffel Tower | Construction began in 1887 and was completed in 1889. [2] London | ... "
                    "Relevant passages: [1] because it directly states completion year."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise search query.",
                "stage_action": (
                    "Based on the filtered passages, determine the single most important fact still missing for verification. "
                    "Write a concise, specific search query to find this evidence. "
                    "Output ONLY the search query with no additional text or explanations."
                ),
                "reasoning_questions": (
                    "What specific fact is missing that is most crucial for verification? "
                    "How can we phrase a query that precisely targets this missing information? "
                    "What entities from the claim should be included in the query?"
                ),
                "example_reasoning": "Example: 'Eiffel Tower construction start year'",
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
            # Step 5: Generate third-hop query
            {
                "number": 5,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the next missing evidence using all available context and generate a precise query.",
                "stage_action": (
                    "Based on the filtered first-hop evidence (step2) and second-hop passages (step4), "
                    "determine the most critical missing fact for verification. "
                    "Write a concise search query to find this evidence. "
                    "Output ONLY the search query with no additional text."
                ),
                "reasoning_questions": (
                    "What fact is still missing after reviewing both hops? "
                    "How can we phrase a query that incorporates context from multiple hops? "
                    "What specific detail would confirm or refute the claim?"
                ),
                "example_reasoning": "Example: 'Marie Curie Nobel Prize years'",
                "dependencies": [2, 4],
            },
            # Step 6: Third-hop retrieval
            {
                "number": 6,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 7: Evidence synthesis
            {
                "number": 7,
                "title": "Synthesize evidence and verify",
                "step_type": "llm",
                "aim": "Determine if the claim is fully supported by all retrieved evidence.",
                "stage_action": (
                    "Review all relevant passages (steps 2, 4, 6) and assess if they collectively verify the claim. "
                    "If verified, state 'VERIFIED' and list supporting facts. "
                    "If not, state 'UNVERIFIED' and specify the missing evidence required."
                ),
                "reasoning_questions": (
                    "Do the passages confirm every element of the claim? "
                    "What specific information is still missing? "
                    "How confident are we in the verification based on the evidence?"
                ),
                "example_reasoning": (
                    "Example: Claim 'Moon landing occurred in 1969.' Evidence: "
                    "Step2: [1] Apollo 11 | ... launched July 16, 1969. "
                    "Step4: [0] Moon landing | ... on July 20, 1969. "
                    "Step6: [0] NASA | Confirmed lunar module landing. "
                    "Conclusion: VERIFIED - All elements confirmed."
                ),
                "dependencies": [2, 4, 6],
            },
        ],
    }