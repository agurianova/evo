def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Focus on identifying gaps in the current evidence and generating precise search queries to fill those gaps. Always anchor your reasoning to the original claim.",
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
                "aim": "Identify most immediate missing evidence and generate precise search query",
                "stage_action": (
                    "Analyze the claim and first-hop passages to determine the most urgent missing fact. "
                    "Formulate a concise search query targeting this immediate gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What is the most immediate missing fact or date? Which specific entity requires verification first?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | She won the Nobel Prize in Physics in 1903.\n"
                    "Analysis: Confirms one prize but omits second award details.\n"
                    "Missing: Field and year of second Nobel Prize.\n"
                    "Query: 'Marie Curie second Nobel Prize field year'"
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
                "aim": "Identify compound gaps in accumulated evidence and generate precise search query",
                "stage_action": (
                    "Synthesize first and second-hop passages to find missing relationships between entities. "
                    "Formulate a concise query targeting compound gaps. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What relationship between entities remains unverified? Which two facts need connecting to support the claim?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | Physics prize 1903. [2] Chemistry Nobel | 1911 award to Curie.\n"
                    "Analysis: Confirms two prizes but lacks explicit statement that Chemistry was her second award.\n"
                    "Missing: Connection between 1911 Chemistry prize and 'second Nobel Prize' status.\n"
                    "Query: 'Marie Curie second Nobel Prize Chemistry 1911 confirmation'"
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
                "aim": "Identify gaps requiring authoritative verification and generate final search query",
                "stage_action": (
                    "Analyze all evidence to find aspects needing official confirmation. "
                    "Formulate a query targeting authoritative sources. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What claim aspect lacks verification from official records? Which detail needs institutional confirmation?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Physics 1903. [2] Chemistry 1911. [3] Nobel lists confirm both.\n"
                    "Analysis: All prizes documented but lack official Nobel Prize statement.\n"
                    "Missing: Primary source confirming dual awards from Nobel organization.\n"
                    "Query: 'Official Nobel Prize records Marie Curie two awards'"
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