def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims through multi-hop evidence retrieval. Your goal is to maximize coverage of supporting documents by identifying precise information gaps and generating targeted search queries. At each step, assess whether the evidence gathered so far is sufficient to verify the claim or if additional retrieval hops are needed. Always prioritize claim-specific evidence and avoid irrelevant information.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve initial evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate first gap query
            {
                "number": 2,
                "title": "Identify first critical gap and generate query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence after first retrieval and generate precise search query for one gap",
                "stage_action": (
                    "Analyze the retrieved passages and determine what specific information is missing "
                    "to verify the claim. Generate ONLY a concise search query targeting this gap."
                ),
                "reasoning_questions": (
                    "What specific fact or detail from the claim is NOT addressed by the retrieved passages?"
                    "\nWhich entities or relationships need further verification?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes in different sciences.'"
                    "\nRetrieved: [0] Marie Curie | She won Nobel Prize in Physics (1903)"
                    "\nMissing: Nobel Prize in Chemistry (1911)"
                    "\nQuery: 'Marie Curie Nobel Prize Chemistry 1911'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second gap query (distinct from first)
            {
                "number": 3,
                "title": "Identify second critical gap (distinct from first) and generate query",
                "step_type": "llm",
                "aim": "Identify a different critical missing evidence (distinct from the first gap) and generate precise search query for this second gap",
                "stage_action": (
                    "Analyze the retrieved passages and the first gap query (from previous step) to determine a different specific piece of missing information. "
                    "Generate ONLY a concise search query targeting this second gap."
                ),
                "reasoning_questions": (
                    "What specific fact or detail is missing that is NOT covered by the first gap query?"
                    "\nWhich other entities/relationships require verification?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended as a temporary structure.'"
                    "\nRetrieved: [0] Eiffel Tower | Built for 1889 World's Fair"
                    "\nFirst gap query: 'Eiffel Tower permission duration'"
                    "\nSecond gap: Decision timeline for permanent status"
                    "\nQuery: 'Eiffel Tower permanent status decision year'"
                ),
                "dependencies": [1, 2],
            },
            # Step 4: First parallel retrieval
            {
                "number": 4,
                "title": "Retrieve evidence for first gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Second parallel retrieval
            {
                "number": 5,
                "title": "Retrieve evidence for second gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Synthesize evidence and generate final query
            {
                "number": 6,
                "title": "Synthesize evidence and generate final query",
                "step_type": "llm",
                "aim": "Combine evidence from all retrievals and identify the single most critical remaining gap",
                "stage_action": (
                    "Comprehensively review ALL retrieved evidence (initial and both parallel retrievals). "
                    "Identify the SINGLE most critical missing piece of information and generate ONLY a concise "
                    "search query targeting this gap. ALWAYS generate a meaningful query even if the claim appears verified."
                ),
                "reasoning_questions": (
                    "Based on ALL evidence gathered so far, what is the SINGLE most critical missing fact?"
                    "\nWhat unverified entity/relationship remains essential for the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Polar bears can swim 60 miles without resting.'"
                    "\nRetrieved: [0] Polar bear | Excellent swimmers, travel long distances"
                    "\nRetrieved: [1] Marine mammal journal | Documented 50-mile swim"
                    "\nRetrieved: [2] Arctic study | Observed 40-mile swims regularly"
                    "\nMissing: Verified record of 60-mile swim"
                    "\nQuery: 'Polar bear maximum swimming distance record'"
                ),
                "dependencies": [1, 4, 5],
            },
            # Step 7: Final retrieval
            {
                "number": 7,
                "title": "Retrieve final evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }