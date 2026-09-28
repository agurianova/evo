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
                    "The claim states that 'Climate change is caused by human activities'. The first-hop passages mention climate change and human activities but do not establish causation. "
                    "To verify causation, I need evidence of a causal mechanism or experimental results. "
                    "Query: 'evidence that human activities cause climate change'"
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
                    "The first-hop passages mention climate change and human activities without establishing causation. The second-hop passages show correlation between CO2 levels and rising global temperatures but do not rule out natural causes. "
                    "I need evidence that rules out natural causes. "
                    "Query: 'evidence that climate change is not caused by natural factors'"
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
                    "The first-hop passages mention climate change and human activities without causation. The second-hop shows correlation but not causation. The third-hop rules out natural causes but does not provide a definitive causal mechanism. "
                    "I need evidence of a direct causal link. "
                    "Query: 'how do greenhouse gases cause global warming'"
                ),
                "dependencies": [5],
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