def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checking assistant. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. Always be precise and methodical.",
        "steps": [
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
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop passages, determine what additional evidence is needed to "
                    "verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is missing to verify the claim?\n"
                    "2. Which entity is central to this missing fact?\n"
                    "3. What precise terms (e.g., technical terms, specific dates) should be included in the query to retrieve relevant information?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Passages: [0] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "Missing fact: Whether 'built' refers to the start year or completion year in construction context.\n"
                    "Central entity: construction of Eiffel Tower\n"
                    "Precise terms: 'construction start vs completion date meaning'\n"
                    "Query: construction start vs completion date meaning"
                ),
                "dependencies": [1],
            },
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
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a precise search query for the third hop.",
                "stage_action": (
                    "Based on the retrieved passages from the first and second hops, determine what additional evidence is needed to "
                    "verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is missing to verify the claim?\n"
                    "2. Which entity is central to this missing fact?\n"
                    "3. What precise terms (e.g., technical terms, specific dates) should be included in the query to retrieve relevant information?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Passages: [0] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "Passages: [0] Building construction | The term 'built' in construction projects typically refers to the completion date.\n"
                    "Missing fact: The completion date of the Eiffel Tower.\n"
                    "Central entity: Eiffel Tower\n"
                    "Precise terms: 'Eiffel Tower completion date'\n"
                    "Query: Eiffel Tower completion date"
                ),
                "dependencies": [1, 3],
            },
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
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a precise search query for the fourth hop.",
                "stage_action": (
                    "Based on the retrieved passages from the first, second, and third hops, determine what additional evidence is needed to "
                    "verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is missing to verify the claim?\n"
                    "2. Which entity is central to this missing fact?\n"
                    "3. What precise terms (e.g., technical terms, specific dates) should be included in the query to retrieve relevant information?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Passages from first hop: [0] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "Passages from second hop: [0] Building construction | The term 'built' in construction projects typically refers to the completion date.\n"
                    "Passages from third hop: [0] Eiffel Tower | The Eiffel Tower was completed on March 15, 1889.\n"
                    "Missing fact: None. The claim states 'built in 1887', but we have evidence that construction began in 1887 and completed in 1889. However, the claim might be false if 'built' means completed. But we have the completion date. So no missing fact? Actually, we need to confirm the meaning of 'built'. But the second hop already explained that. So we have all evidence.\n"
                    "However, to be thorough, we might check: is there any source that uses 'built' for the start year? But the claim is likely false.\n"
                    "In this case, we can generate a query for: 'Eiffel Tower built meaning start or completion'\n"
                    "Query: Eiffel Tower built meaning start or completion"
                ),
                "dependencies": [1, 3, 5],
            },
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