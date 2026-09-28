def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving supporting evidence from Wikipedia. Focus on identifying gaps in the evidence relative to the original claim and generating precise search queries to fill those gaps.",
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
                "aim": "Identify missing information relative to the original claim and generate a search query for the next hop.",
                "stage_action": (
                    "Based on the retrieved passages from the previous step and the original claim (provided in Data), "
                    "determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query to find the missing evidence. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "1. What does the original claim state that hasn't been confirmed by the retrieved passages?\n"
                    "2. What specific information is missing to verify the claim?\n"
                    "3. How can we phrase a search query to find the missing information?"
                ),
                "example_reasoning": (
                    "Original claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Retrieved passages: [Passages about Eiffel Tower construction, but none mention duration.]\n"
                    "Gap analysis: Passages confirm construction details but omit intended permanence.\n"
                    "Query: 'Eiffel Tower temporary structure intended duration'"
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
                "aim": "Identify missing information relative to the original claim and generate a search query for the next hop.",
                "stage_action": (
                    "Based on the retrieved passages from the previous step and the original claim (provided in Data), "
                    "determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query to find the missing evidence. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "1. What does the original claim state that hasn't been confirmed by the retrieved passages?\n"
                    "2. What specific information is missing to verify the claim?\n"
                    "3. How can we phrase a search query to find the missing information?"
                ),
                "example_reasoning": (
                    "Original claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Retrieved passages: [Passages mention 20-year permit but not 'temporary' intent.]\n"
                    "Gap analysis: Evidence shows time-bound permit but doesn't confirm designers' intent.\n"
                    "Query: 'Eiffel Tower designers intended temporary structure purpose'"
                ),
                "dependencies": [3],
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
                "aim": "Identify missing information relative to the original claim and generate a search query for the next hop.",
                "stage_action": (
                    "Based on the retrieved passages from the previous step and the original claim (provided in Data), "
                    "determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query to find the missing evidence. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "1. What does the original claim state that hasn't been confirmed by the retrieved passages?\n"
                    "2. What specific information is missing to verify the claim?\n"
                    "3. How can we phrase a search query to find the missing information?"
                ),
                "example_reasoning": (
                    "Original claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Retrieved passages: [Passages confirm 1889 construction and 1909 removal plan.]\n"
                    "Gap analysis: Evidence shows removal plan but lacks explicit 'temporary' design intent.\n"
                    "Query: 'Eiffel Tower Gustave Eiffel temporary structure statement'"
                ),
                "dependencies": [5],
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