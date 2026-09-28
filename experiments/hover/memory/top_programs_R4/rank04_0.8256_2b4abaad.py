def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims through multi-hop evidence retrieval. Your goal is to maximize coverage of supporting documents by identifying precise information gaps and generating targeted search queries. At each step, assess whether the evidence gathered so far is sufficient to verify the claim or if additional retrieval hops are needed. Always prioritize claim-specific evidence and avoid irrelevant information. Your performance is measured by fractional retrieval coverage (the fraction of gold supporting documents found), so prioritize retrieving as many relevant documents as possible.",
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
            # Step 2: Generate second-hop query with sufficiency check
            {
                "number": 2,
                "title": "Identify first gap and generate query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence after initial retrieval and generate precise search query, or output 'STOP' if sufficient",
                "stage_action": (
                    "Analyze the retrieved passages from step 1. If the evidence gathered so far is sufficient to verify the claim, output 'STOP'. "
                    "Otherwise, identify the most critical missing evidence and generate ONLY a concise search query targeting this gap. "
                    "Ensure the query uses new entities not present in the claim or previous queries."
                ),
                "reasoning_questions": (
                    "Is the evidence gathered so far sufficient to verify the claim? If not, what specific fact or detail is missing?"
                    "\nWhich entities or relationships need further verification?"
                    "\nHow can we formulate a query with new entities not used in the claim?"
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
            # Step 4: Generate first critical gap query for third hop
            {
                "number": 4,
                "title": "Identify first critical gap and generate query",
                "step_type": "llm",
                "aim": "Identify the single most critical missing evidence after first two retrievals and generate precise search query, or output 'STOP' if sufficient",
                "stage_action": (
                    "Analyze the retrieved passages from steps 1 and 3. If the evidence gathered so far is sufficient to verify the claim, output 'STOP'. "
                    "Otherwise, identify the single most critical missing evidence and generate ONLY a concise search query targeting this gap. "
                    "Ensure the query uses new entities not present in previous queries."
                ),
                "reasoning_questions": (
                    "Is the evidence gathered so far sufficient to verify the claim? If not, what specific fact or detail is missing?"
                    "\nWhich entity or relationship remains most unverified?"
                    "\nWhat is the highest-impact missing piece for claim verification?"
                    "\nHow can we formulate a query with new entities not used in prior queries?"
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
            # Step 5: Retrieve evidence for first critical gap
            {
                "number": 5,
                "title": "Retrieve evidence for first critical gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate next critical gap query with updated evidence
            {
                "number": 6,
                "title": "Identify next critical gap and generate query",
                "step_type": "llm",
                "aim": "Identify the next most critical missing evidence after three retrievals and generate precise search query, or output 'STOP' if sufficient",
                "stage_action": (
                    "Analyze the retrieved passages from steps 1, 3, and 5. If the evidence gathered so far is sufficient to verify the claim, output 'STOP'. "
                    "Otherwise, identify the next most critical missing evidence (distinct from the gap targeted in step 4) and generate ONLY a concise search query targeting this gap. "
                    "Ensure the query uses new entities not present in previous queries."
                ),
                "reasoning_questions": (
                    "Is the evidence gathered so far sufficient to verify the claim? If not, what specific fact or detail is missing beyond the gap targeted in step 4?"
                    "\nWhich secondary entity or relationship needs verification?"
                    "\nWhat is the next highest-impact missing piece for claim verification?"
                    "\nHow can we formulate a query with new entities not used in prior queries?"
                ),
                "example_reasoning": (
                    "Claim: 'The Great Wall of China was built over several dynasties, starting in the 7th century BC.'"
                    "\nRetrieved: [0] Great Wall of China | Initial construction began during the Spring and Autumn period"
                    "\nRetrieved: [1] Qin dynasty | Connected existing walls in 221–206 BC"
                    "\nRetrieved: [2] Han dynasty | Extended the wall into the Hexi Corridor"
                    "\nMissing: Specific role of the Ming dynasty in wall construction"
                    "\nQuery: 'Great Wall Ming dynasty construction period'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Retrieve evidence for next critical gap
            {
                "number": 7,
                "title": "Retrieve evidence for next critical gap",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }