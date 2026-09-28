def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims through multi-hop evidence retrieval. Your goal is to maximize coverage of supporting documents by identifying precise information gaps and generating targeted search queries. At each step, assess whether the evidence gathered so far is sufficient to verify the claim or if additional retrieval hops are needed. Always prioritize claim-specific evidence and avoid irrelevant information. Your performance is measured by the fraction of gold supporting documents retrieved across all hops; aim for >0.7 coverage.",
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
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Assess evidence and generate final query",
                "step_type": "llm",
                "aim": "Determine critical gaps and generate query for additional evidence",
                "stage_action": (
                    "Comprehensively review ALL retrieved evidence. Identify the SINGLE most important "
                    "missing piece of evidence or opportunity to find additional supporting evidence. "
                    "Generate ONLY a concise search query targeting this gap or opportunity."
                ),
                "reasoning_questions": (
                    "After reviewing ALL evidence, what is the SINGLE most important missing fact?"
                    "\nCould additional sources strengthen the verification?"
                    "\nWould another retrieval hop likely find this information?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes in different sciences.'"
                    "\nRetrieved: [0] Marie Curie | She won Nobel Prize in Physics (1903)"
                    "\nRetrieved: [1] Nobel Prize archive | Marie Curie awarded Chemistry Nobel (1911)"
                    "\nAssessment: Claim is verified, but additional sources could strengthen coverage"
                    "\nQuery: 'Marie Curie two Nobel Prizes official records'"
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