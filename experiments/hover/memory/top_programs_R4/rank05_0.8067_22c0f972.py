def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims through multi-hop evidence retrieval. Your goal is to maximize the fraction of gold supporting documents retrieved (retrieval coverage) by identifying precise information gaps and generating targeted search queries. At each step, assess what specific information is still missing to verify the claim and generate a search query for that gap. Even if the claim seems verified, generate a query to seek additional confirmation or context to ensure completeness. Always prioritize claim-specific evidence and avoid irrelevant information.",
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
                    "is still missing to verify the claim. If no gap is found, generate a query that seeks additional confirmation. "
                    "Generate ONLY a concise search query."
                ),
                "reasoning_questions": (
                    "Based on ALL evidence gathered so far, what specific information is still missing?"
                    "\nAre there conflicting details that need resolution?"
                    "\nWhat entities/relationships remain unverified?"
                    "\nIf evidence is sufficient, what query would confirm it beyond doubt?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes.'"
                    "\nRetrieved: [0] Marie Curie | She won Nobel Prize in Physics (1903) and Chemistry (1911)"
                    "\nAssessment: Evidence fully verifies the claim."
                    "\nQuery: 'Marie Curie two Nobel Prizes confirmation'"
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
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Assess evidence completeness and generate query",
                "step_type": "llm",
                "aim": "Determine critical missing evidence and generate final query",
                "stage_action": (
                    "Comprehensively review ALL retrieved evidence. Identify the single most critical missing piece "
                    "and generate ONLY a concise search query targeting this gap. If no gap is found, generate a query "
                    "that seeks additional confirmation."
                ),
                "reasoning_questions": (
                    "After reviewing ALL evidence, what is the SINGLE most important missing fact?"
                    "\nWould another retrieval hop likely find this information?"
                    "\nIf evidence is sufficient, what query would provide definitive confirmation?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower is located in Paris.'"
                    "\nRetrieved: [0] Eiffel Tower | Built in Paris for the 1889 World's Fair"
                    "\nRetrieved: [1] Paris | Capital city of France, home to the Eiffel Tower"
                    "\nRetrieved: [2] World Heritage site | The Eiffel Tower in Paris"
                    "\nAssessment: Evidence fully verifies the claim."
                    "\nQuery: 'Eiffel Tower location confirmation Paris'"
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