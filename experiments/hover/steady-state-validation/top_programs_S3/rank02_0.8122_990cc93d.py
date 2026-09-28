def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims using Wikipedia evidence. Decompose claims into subject/object entities for parallel evidence gathering. Be precise: when asked for a search query, output ONLY the query string with no additional text. If no more evidence is needed, output an empty string.",
        "steps": [
            # Step 1: Generate subject-focused query
            {
                "number": 1,
                "title": "Generate subject query",
                "step_type": "llm",
                "aim": "Extract subject entity and generate targeted search query",
                "stage_action": "Identify the main subject of the claim. Generate a concise search query focused on the subject's relevant attributes and relationships. Output ONLY the query string.",
                "reasoning_questions": "What is the central subject? What key properties of this subject relate to the claim's verification?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.' → Subject: 'Eiffel Tower', Query: 'Eiffel Tower original intended city'",
                "dependencies": [],
            },
            # Step 2: Generate object-focused query
            {
                "number": 2,
                "title": "Generate object query",
                "step_type": "llm",
                "aim": "Extract object entity and generate targeted search query",
                "stage_action": "Identify the main object of the claim. Generate a concise search query focused on the object's role in the claim. Output ONLY the query string.",
                "reasoning_questions": "What is the primary object? How does it interact with the subject in the claim context?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.' → Object: 'Barcelona', Query: 'Barcelona Eiffel Tower proposal history'",
                "dependencies": [],
            },
            # Step 3: Deep retrieval for subject
            {
                "number": 3,
                "title": "Retrieve subject passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[0]"},
                },
                "dependencies": [1],
            },
            # Step 4: Deep retrieval for object
            {
                "number": 4,
                "title": "Retrieve object passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Synthesize evidence and generate next query
            {
                "number": 5,
                "title": "Synthesize evidence and generate hop2 query",
                "step_type": "llm",
                "aim": "Synthesize evidence from all retrieved passages and generate next query if needed",
                "stage_action": "Review all retrieved passages from previous steps. If the claim is fully verified, output an empty string. Otherwise, identify the critical missing information and generate a precise search query to retrieve it. Output ONLY the query string or empty string with no additional text.",
                "reasoning_questions": "What aspects of the claim are confirmed by the evidence? What single piece of information is still missing to verify the claim?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.' Verified: built in Paris, Barcelona rejected proposal → Missing: rejection reason → Query: 'Eiffel Tower Barcelona rejection reason'",
                "dependencies": [3, 4],
            },
            # Step 6: Deep retrieval for hop2
            {
                "number": 6,
                "title": "Retrieve hop2 passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 7: Synthesize evidence and generate next query
            {
                "number": 7,
                "title": "Synthesize evidence and generate hop3 query",
                "step_type": "llm",
                "aim": "Synthesize evidence from all retrieved passages and generate next query if needed",
                "stage_action": "Review all retrieved passages from previous steps. If the claim is fully verified, output an empty string. Otherwise, identify the critical missing information and generate a precise search query to retrieve it. Output ONLY the query string or empty string with no additional text.",
                "reasoning_questions": "What aspects of the claim are confirmed by the evidence? What single piece of information is still missing to verify the claim?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.' Verified: built in Paris, Barcelona rejected proposal, rejection due to budget → Missing: rejection date → Query: 'Barcelona Eiffel Tower proposal rejection date'",
                "dependencies": [3, 4, 6],
            },
            # Step 8: Deep retrieval for hop3
            {
                "number": 8,
                "title": "Retrieve hop3 passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            # Step 9: Synthesize evidence and generate next query
            {
                "number": 9,
                "title": "Synthesize evidence and generate hop4 query",
                "step_type": "llm",
                "aim": "Synthesize evidence from all retrieved passages and generate next query if needed",
                "stage_action": "Review all retrieved passages from previous steps. If the claim is fully verified, output an empty string. Otherwise, identify the critical missing information and generate a precise search query to retrieve it. Output ONLY the query string or empty string with no additional text.",
                "reasoning_questions": "What aspects of the claim are confirmed by the evidence? What single piece of information is still missing to verify the claim?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.' Verified: built in Paris, Barcelona rejected proposal, rejection due to budget, rejection date 1889 → Missing: none → Output: ''",
                "dependencies": [3, 4, 6, 8],
            },
            # Step 10: Deep retrieval for hop4
            {
                "number": 10,
                "title": "Retrieve hop4 passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }
