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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Identify first gap and generate query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence after first retrieval and generate precise search query",
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
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Identify intermediate gap and generate query",
                "step_type": "llm",
                "aim": "Synthesize all evidence and identify remaining gaps for third retrieval",
                "stage_action": (
                    "Combine evidence from both retrievals and determine what specific information "
                    "is still missing to verify the claim. Generate ONLY a concise search query "
                    "targeting this gap."
                ),
                "reasoning_questions": (
                    "Based on ALL evidence gathered so far, what specific information is still missing?"
                    "\nAre there conflicting details that need resolution?"
                    "\nWhat entities/relationships remain unverified?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended as a temporary structure.'"
                    "\nRetrieved: [0] Eiffel Tower | Built for 1889 World's Fair"
                    "\nRetrieved: [1] Gustave Eiffel | Contract allowed demolition after 20 years"
                    "\nMissing: Official decision to keep it permanently"
                    "\nQuery: 'Eiffel Tower permanent status decision 1909'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate fourth-hop query (always generate query)
            {
                "number": 6,
                "title": "Assess evidence and generate final query",
                "step_type": "llm",
                "aim": "Identify the most critical remaining gap and generate final query",
                "stage_action": (
                    "Comprehensively review ALL retrieved evidence. Identify the SINGLE most critical missing piece "
                    "of information to verify the claim and generate ONLY a concise search query targeting this gap."
                ),
                "reasoning_questions": (
                    "After reviewing ALL evidence, what specific information is still missing to fully verify the claim? Consider if there are multiple gaps and prioritize the most critical one."
                    "\nWhat entity or relationship remains unverified that is essential for the claim?"
                    "\nWould a targeted query for this gap likely retrieve the missing evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'Polar bears can swim 60 miles without resting.'"
                    "\nRetrieved: [0] Polar bear | Excellent swimmers, travel long distances"
                    "\nRetrieved: [1] Marine mammal journal | Documented 50-mile swim"
                    "\nRetrieved: [2] Arctic study | Observed 40-mile swims regularly"
                    "\nAssessment: Evidence shows long swims but not the specific 60-mile claim"
                    "\nQuery: 'Polar bear maximum swimming distance record'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
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