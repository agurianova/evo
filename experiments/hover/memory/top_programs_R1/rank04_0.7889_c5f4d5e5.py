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
                "aim": "Identify gaps in first-hop evidence and generate precise search query",
                "stage_action": (
                    "Analyze the claim and retrieved passages to determine missing evidence. "
                    "Formulate a concise search query targeting the gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks support? Which entities/relationships need verification?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | She won the Nobel Prize in Physics in 1903.\n"
                    "Analysis: Passages confirm one prize but omit the second.\n"
                    "Missing: field and year of second Nobel Prize.\n"
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
                "aim": "Identify gaps in first+second-hop evidence and generate precise search query",
                "stage_action": (
                    "Analyze the claim and all retrieved passages to determine missing evidence. "
                    "Formulate a concise search query targeting the gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks support? Which entities/relationships need verification?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | She won the Nobel Prize in Physics in 1903. [2] ... \n"
                    "Analysis: Passages confirm Physics prize but omit Chemistry prize details.\n"
                    "Missing: confirmation of Chemistry prize and year.\n"
                    "Query: 'Marie Curie Nobel Prize in Chemistry year'"
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
                "aim": "Identify remaining gaps and generate final search query",
                "stage_action": (
                    "Analyze the claim and all retrieved passages to determine final missing evidence. "
                    "Formulate a concise search query targeting the gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks support? Which entities/relationships need verification?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] ... [2] ... [3] ... \n"
                    "Analysis: All prizes are mentioned but lack official verification source.\n"
                    "Missing: Official Nobel Prize records confirming both awards.\n"
                    "Query: 'Nobel Prize official records Marie Curie'"
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