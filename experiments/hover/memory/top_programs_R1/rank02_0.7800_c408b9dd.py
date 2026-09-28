def entrypoint():
    return {
        "system_prompt": "You are a fact-checking assistant. Your task is to verify claims by gathering evidence from Wikipedia. Always focus on finding supporting or refuting evidence. Be precise and concise.",
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
                "aim": "Identify gaps in current evidence and generate search query for next evidence",
                "stage_action": (
                    "Review the claim and all provided evidence passages. Enumerate exactly what evidence is still missing to verify the claim. "
                    "Then, write a concise search query to find that missing evidence. Output exactly one line of text: the search query."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to verify the claim? "
                    "What keywords would appear in a passage containing that fact?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages mention construction started in 1887 but don't state completion year.\n"
                    "Missing: Completion year of the Eiffel Tower.\n"
                    "Query: 'Eiffel Tower completion year'"
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
                "aim": "Identify gaps in current evidence and generate search query for next evidence",
                "stage_action": (
                    "Review the claim and all provided evidence passages. Enumerate exactly what evidence is still missing to verify the claim. "
                    "Then, write a concise search query to find that missing evidence. Output exactly one line of text: the search query."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to verify the claim? "
                    "What keywords would appear in a passage containing that fact?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages mention construction started in 1887 but don't state completion year.\n"
                    "Missing: Completion year of the Eiffel Tower.\n"
                    "Query: 'Eiffel Tower completion year'"
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
                "aim": "Identify gaps in current evidence and generate search query for next evidence",
                "stage_action": (
                    "Review the claim and all provided evidence passages. Enumerate exactly what evidence is still missing to verify the claim. "
                    "Then, write a concise search query to find that missing evidence. Output exactly one line of text: the search query."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to verify the claim? "
                    "What keywords would appear in a passage containing that fact?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages mention construction started in 1887 but don't state completion year.\n"
                    "Missing: Completion year of the Eiffel Tower.\n"
                    "Query: 'Eiffel Tower completion year'"
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