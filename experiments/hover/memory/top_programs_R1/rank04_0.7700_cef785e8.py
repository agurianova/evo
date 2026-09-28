def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Focus on identifying gaps in the current evidence and generating precise search queries to fill those gaps.",
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
                "aim": "Identify missing information for claim verification and generate a precise search query for the next hop.",
                "stage_action": (
                    "Analyze the retrieved passages and the original claim to determine what specific information is still missing to verify the claim. "
                    "Write a concise search query that targets the missing evidence. "
                    "Output exactly one line of text: the search query, with no other content."
                ),
                "reasoning_questions": (
                    "What is the original claim? "
                    "What evidence have we found in the retrieved passages? "
                    "What specific piece of information is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "Retrieved passages:\n"
                    "[1] Eiffel Tower | The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France.\n"
                    "[2] History of the Eiffel Tower | It was constructed from 1887 to 1889 as the centerpiece of the 1889 World's Fair.\n"
                    "Analysis: The claim mentions Barcelona, but the retrieved passages only discuss Paris. The missing information is the original intended location of the Eiffel Tower.\n"
                    "Query: 'Eiffel Tower original intended location'"
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
                "aim": "Identify missing information for claim verification and generate a precise search query for the next hop.",
                "stage_action": (
                    "Analyze the retrieved passages and the original claim to determine what specific information is still missing to verify the claim. "
                    "Write a concise search query that targets the missing evidence. "
                    "Output exactly one line of text: the search query, with no other content."
                ),
                "reasoning_questions": (
                    "What is the original claim? "
                    "What evidence have we found in the retrieved passages? "
                    "What specific piece of information is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "Retrieved passages:\n"
                    "[1] Gustave Eiffel | The French engineer Gustave Eiffel designed the Eiffel Tower.\n"
                    "[2] Barcelona history | Barcelona was considered for the 1888 World's Fair but rejected.\n"
                    "Analysis: We have engineer's name and Barcelona's fair rejection, but need confirmation of initial location proposal.\n"
                    "Query: 'Eiffel Tower Barcelona proposal'"
                ),
                "dependencies": [3],
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
                "aim": "Identify missing information for claim verification and generate a precise search query for the next hop.",
                "stage_action": (
                    "Analyze the retrieved passages and the original claim to determine what specific information is still missing to verify the claim. "
                    "Write a concise search query that targets the missing evidence. "
                    "Output exactly one line of text: the search query, with no other content."
                ),
                "reasoning_questions": (
                    "What is the original claim? "
                    "What evidence have we found in the retrieved passages? "
                    "What specific piece of information is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "Retrieved passages:\n"
                    "[1] Eiffel's memoirs | 'I presented the Barcelona city council with plans for a 300-meter tower.'\n"
                    "[2] 1889 World's Fair records | Contract signed with Paris on January 8, 1887.\n"
                    "Analysis: We have proof of Barcelona proposal and Paris contract, but need confirmation it was rejected by Barcelona.\n"
                    "Query: 'Barcelona reject Eiffel Tower proposal'"
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