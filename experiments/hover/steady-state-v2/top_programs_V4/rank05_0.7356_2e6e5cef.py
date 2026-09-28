def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier for multi-hop claim verification. Your goal is to retrieve all supporting documents by performing sequential searches. Be thorough and precise. For query generation steps, output ONLY the search query or 'STOP' with no additional text.",
        "steps": [
            # Step 1: First-hop retrieval (deep search for broad coverage)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that are directly relevant to verifying the claim. "
                    "Summarize the most important evidence found, focusing on facts that support or refute the claim."
                ),
                "reasoning_questions": (
                    "What are the main entities and events mentioned? "
                    "How do these relate to the claim? "
                    "Are there any contradictions or missing pieces?"
                ),
                "example_reasoning": (
                    "The passage states that the event occurred in 2010, which contradicts the claim's year of 2015. "
                    "Key fact: event year is 2010."
                ),
                "dependencies": [1],
            },
            # Step 3: First continuation decision
            {
                "number": 3,
                "title": "First continuation decision",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient or if a second hop is needed.",
                "stage_action": (
                    "Review the first-hop summary and the claim. If the evidence is complete, output 'STOP'. "
                    "Otherwise, output a broad search query to find the main missing piece of evidence. "
                    "Output ONLY the word 'STOP' or the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Is the current evidence sufficient to verify the claim? "
                    "If not, what specific information is missing? "
                    "How can we formulate a precise query for the missing information?"
                ),
                "example_reasoning": "When did the event occur?",
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
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that are directly relevant to verifying the claim. "
                    "Summarize the most important evidence found, focusing on facts that support or refute the claim."
                ),
                "reasoning_questions": (
                    "What are the main entities and events mentioned? "
                    "How do these relate to the claim? "
                    "Are there any contradictions or missing pieces?"
                ),
                "example_reasoning": (
                    "The passage confirms the event occurred in 2010 with a government report dated January 2010. "
                    "Key fact: official confirmation in January 2010."
                ),
                "dependencies": [4],
            },
            # Step 6: Second continuation decision
            {
                "number": 6,
                "title": "Second continuation decision",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient or if a third hop is needed.",
                "stage_action": (
                    "Review the first-hop and second-hop summaries and the claim. "
                    "If the evidence is complete, output 'STOP'. "
                    "Otherwise, output a specific search query targeting the exact missing detail. "
                    "Output ONLY the word 'STOP' or the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Is the current evidence sufficient to verify the claim? "
                    "If not, what specific information is missing? "
                    "How can we formulate a precise query for the missing information?"
                ),
                "example_reasoning": "What was the exact date of the event in 2010?",
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
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that are directly relevant to verifying the claim. "
                    "Summarize the most important evidence found, focusing on facts that support or refute the claim."
                ),
                "reasoning_questions": (
                    "What are the main entities and events mentioned? "
                    "How do these relate to the claim? "
                    "Are there any contradictions or missing pieces?"
                ),
                "example_reasoning": (
                    "The passage provides the exact date: January 15, 2010, from the government report. "
                    "Key fact: event date is January 15, 2010."
                ),
                "dependencies": [7],
            },
            # Step 9: Third continuation decision
            {
                "number": 9,
                "title": "Third continuation decision",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient or if a fourth hop is needed.",
                "stage_action": (
                    "Review all evidence summaries so far and the claim. "
                    "If the evidence is complete, output 'STOP'. "
                    "Otherwise, output a very specific search query for the final missing piece. "
                    "Output ONLY the word 'STOP' or the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Is the current evidence sufficient to verify the claim? "
                    "If not, what specific information is missing? "
                    "How can we formulate a precise query for the missing information?"
                ),
                "example_reasoning": "Was the event confirmed by the government report?",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deep search for final gaps)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }