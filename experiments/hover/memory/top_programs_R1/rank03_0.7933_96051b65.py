def entrypoint():
    return {
        "system_prompt": "You are a multi-hop claim verifier. For query generation steps, output ONLY a minimal search query with key entities (no ORs, no extra text). Always anticipate intermediate evidence needs. Verify claims by accumulating evidence across hops.",
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
            # Step 2: Multi-hop gap analysis & second-hop query
            {
                "number": 2,
                "title": "Identify critical intermediate gap and generate minimal query",
                "step_type": "llm",
                "aim": "Identify the single most critical intermediate fact missing from first-hop evidence and generate minimal query for it.",
                "stage_action": (
                    "Analyze retrieved passages to confirm known facts and identify the single most critical intermediate fact needed to verify the claim. "
                    "Generate a concise search query for that fact. Output ONLY the query."
                ),
                "reasoning_questions": (
                    "What intermediate fact bridges the gap between known evidence and the claim? "
                    "What is the minimal query (key entities only) to retrieve it?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'Marie Curie won two Nobel Prizes'. "
                    "Known: Physics Prize (1903). Missing: Second Nobel Prize. Query: 'Marie Curie second Nobel Prize'"
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
            # Step 4: Dynamic gap re-analysis & third-hop query
            {
                "number": 4,
                "title": "Re-identify gaps from combined evidence and generate minimal query",
                "step_type": "llm",
                "aim": "Re-identify gaps from combined first and second hop evidence, then generate minimal query for next critical fact.",
                "stage_action": (
                    "Analyze all evidence so far to confirm known facts and identify the single most critical remaining gap. "
                    "Generate a concise search query for the next intermediate fact. Output ONLY the query."
                ),
                "reasoning_questions": (
                    "What facts are now confirmed? What critical gap remains? "
                    "What minimal query retrieves the next needed fact?"
                ),
                "example_reasoning": (
                    "Example: Step1: Physics Prize (1903). Step3: Second Nobel Prize (1911). "
                    "Missing: Chemistry Prize. Query: 'Marie Curie second Nobel Prize category'"
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
            # Step 6: Final gap verification & fourth-hop query
            {
                "number": 6,
                "title": "Verify claim completion and generate final query if needed",
                "step_type": "llm",
                "aim": "Determine if claim is verified; if not, generate minimal query for final gap.",
                "stage_action": (
                    "If the claim is fully verified by evidence, output 'NO_ADDITIONAL_EVIDENCE_NEEDED'. "
                    "Otherwise, generate a concise query for the single most critical remaining gap. "
                    "Output ONLY the query or the sentinel."
                ),
                "reasoning_questions": (
                    "Is the claim fully supported? If not, what single missing fact is critical "
                    "and what minimal query retrieves it?"
                ),
                "example_reasoning": (
                    "Example: Step1: Physics Prize. Step3: Second Nobel Prize (1911). Step5: Chemistry Prize. "
                    "Claim verified -> output 'NO_ADDITIONAL_EVIDENCE_NEEDED'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop evidence if needed",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }