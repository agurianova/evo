def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Always focus on the original claim and identify precise gaps in the evidence to formulate targeted search queries.",
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information from the first-hop evidence and generate a targeted search query for the second hop.",
                "stage_action": (
                    "Review the first-hop retrieved passages and the original claim. Identify what specific information is still missing to verify the claim. "
                    "Formulate a concise search query to find that missing information. Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "What key fact from the claim is not addressed by the first-hop evidence? "
                    "What entities or relationships need further verification?"
                ),
                "example_reasoning": (
                    "The claim states that 'X caused Y'. The first-hop passages mention X and Y but do not establish causation. "
                    "To verify causation, I need evidence of a causal mechanism or experimental results. "
                    "Query: 'evidence of causal relationship between X and Y'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
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
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after reviewing first and second-hop evidence and generate a targeted search query for the third hop.",
                "stage_action": (
                    "Review the first-hop and second-hop retrieved passages along with the original claim. "
                    "Identify what specific information is still missing to verify the claim. "
                    "Formulate a concise search query to find that missing information. Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "What aspects of the claim are still unverified? "
                    "What new entities or relationships emerged from the second hop that require further evidence?"
                ),
                "example_reasoning": (
                    "The second-hop passages show that X and Y are correlated but not causal. "
                    "I need evidence that rules out confounding factors. "
                    "Query: 'does correlation between X and Y imply causation'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
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
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final gaps after reviewing all evidence so far and generate a targeted search query for the fourth hop.",
                "stage_action": (
                    "Review the first, second, and third-hop retrieved passages along with the original claim. "
                    "Identify what specific information is still missing to verify the claim. "
                    "Formulate a concise search query to find that missing information. Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "What is the last piece of evidence needed to confirm or refute the claim? "
                    "Is there any remaining ambiguity?"
                ),
                "example_reasoning": (
                    "The third-hop passages discuss possible confounders but do not provide a definitive study. "
                    "I need a controlled experiment. "
                    "Query: 'controlled experiment on X and Y'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }