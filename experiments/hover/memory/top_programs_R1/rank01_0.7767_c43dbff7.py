def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Always prioritize identifying missing evidence gaps for claim verification.",
        "steps": [
            # Step 1: First-hop retrieval with original claim
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
            # Step 2: Generate first query for second hop
            {
                "number": 2,
                "title": "Identify first gap and query",
                "step_type": "llm",
                "aim": "Identify critical missing information from initial evidence and generate first search query.",
                "stage_action": (
                    "Read the retrieved passages. List known facts confirmed by evidence and the single most critical missing information "
                    "needed for verification. Write a concise search query to find this missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key facts are confirmed by the initial evidence? "
                    "What is the single most important missing piece for verification? "
                    "How can this gap be phrased as a precise search query?"
                ),
                "example_reasoning": (
                    "Example: Claim 'X was invented in 1900'. Evidence states X was created by Y. "
                    "Missing: invention year. Query: 'Year X was invented'"
                ),
                "dependencies": [1],
            },
            # Step 3: First query retrieval
            {
                "number": 3,
                "title": "Retrieve with first query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second query for second hop
            {
                "number": 4,
                "title": "Identify second gap and query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after first query retrieval and generate second search query.",
                "stage_action": (
                    "Integrate initial evidence with first query results. List all known facts and identify the next critical missing information. "
                    "Write a concise search query for this remaining gap. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What new facts were found in the first query results? "
                    "What is still missing for complete verification? "
                    "How to phrase a query targeting this specific gap?"
                ),
                "example_reasoning": (
                    "Example: After first retrieval, we know X was created by Y in 1800s. Missing: exact year. "
                    "Query: 'Exact year X was invented'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Second query retrieval
            {
                "number": 5,
                "title": "Retrieve with second query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate third query for second hop
            {
                "number": 6,
                "title": "Identify final gap and query",
                "step_type": "llm",
                "aim": "Identify last gaps after second query retrieval and generate final search query.",
                "stage_action": (
                    "Combine all evidence gathered. List confirmed facts and identify any remaining verification gaps. "
                    "Write a concise search query for the final missing evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the current evidence status? "
                    "What is the last critical piece needed for verification? "
                    "How to phrase the most precise query for this final gap?"
                ),
                "example_reasoning": (
                    "Example: Now we know X was created by Y around 1890. Missing: confirmation of 1890. "
                    "Query: 'X invented 1890 verification'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third query retrieval
            {
                "number": 7,
                "title": "Retrieve with third query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }