def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims using Wikipedia evidence. Decompose claims into subject/object entities for parallel evidence gathering. Be precise: when asked for a search query, output ONLY the query string with no additional text.",
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
            # Step 5: Analyze evidence and generate next query (hop 1)
            {
                "number": 5,
                "title": "Analyze evidence and generate next query (hop 1)",
                "step_type": "llm",
                "aim": "Synthesize initial evidence and generate next-hop query if needed",
                "stage_action": "Review the retrieved passages for subject and object. List verified aspects of the claim. If the claim is fully verified, output an empty string. Otherwise, identify the single most critical missing piece and generate a precise search query for it. Output ONLY the query string or empty string if fully verified.",
                "reasoning_questions": "What claim elements are confirmed by the subject and object evidence? What single missing piece prevents full verification?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.'\nSubject evidence: Eiffel Tower constructed in Paris (1889)\nObject evidence: Barcelona rejected Gustave Eiffel's proposal\nVerified: Tower built in Paris; Barcelona rejected proposal\nMissing: Reason for rejection\nWhy Barcelona rejected Eiffel Tower",
                "dependencies": [3, 4],
            },
            # Step 6: Retrieve second-hop passages
            {
                "number": 6,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 7: Analyze evidence and generate next query (hop 2)
            {
                "number": 7,
                "title": "Analyze evidence and generate next query (hop 2)",
                "step_type": "llm",
                "aim": "Synthesize evidence from first and second hops and generate next-hop query if needed",
                "stage_action": "Review all retrieved passages (subject, object, and second hop). List verified aspects of the claim. If the claim is fully verified, output an empty string. Otherwise, identify the single most critical missing piece and generate a precise search query for it. Output ONLY the query string or empty string if fully verified.",
                "reasoning_questions": "What claim elements are confirmed by all evidence so far? What single missing piece remains critical?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.'\nSubject evidence: Built in Paris\nObject evidence: Barcelona rejected proposal\nSecond-hop evidence: Rejection due to budget constraints and political opposition\nVerified: Tower not built in Barcelona; rejection occurred for financial/political reasons\nMissing: None",
                "dependencies": [3, 4, 6],
            },
            # Step 8: Retrieve third-hop passages
            {
                "number": 8,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            # Step 9: Analyze evidence and generate next query (hop 3)
            {
                "number": 9,
                "title": "Analyze evidence and generate next query (hop 3)",
                "step_type": "llm",
                "aim": "Synthesize evidence from first, second, and third hops and generate next-hop query if needed",
                "stage_action": "Review all retrieved passages. List verified aspects of the claim. If the claim is fully verified, output an empty string. Otherwise, identify the single most critical missing piece and generate a precise search query for it. Output ONLY the query string or empty string if fully verified.",
                "reasoning_questions": "With all evidence combined, what prevents complete verification? What minimal information would resolve remaining doubts?",
                "example_reasoning": "Claim: 'The Eiffel Tower was originally intended for Barcelona.'\nAll evidence confirms construction in Paris, Barcelona's rejection, and rejection reasons. No gaps remain.",
                "dependencies": [3, 4, 6, 8],
            },
            # Step 10: Retrieve fourth-hop passages
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
