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
                "aim": "Identify the most immediate missing evidence in first-hop passages",
                "stage_action": (
                    "Analyze the claim and first-hop passages to determine the most obvious missing fact. "
                    "Formulate a concise search query targeting this gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks direct support? Which specific entity or date needs verification?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | She won the Nobel Prize in Physics in 1903.\n"
                    "Analysis: Passages confirm one prize but omit the second award.\n"
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
                "aim": "Synthesize evidence from first and second hops to identify compound gaps",
                "stage_action": (
                    "Analyze the claim and ALL retrieved passages (first and second hops) to identify missing relationships "
                    "between entities or compound facts. Formulate a concise search query targeting this gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What relationship between entities is missing? How do facts from different passages connect to form a gap?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | She won the Nobel Prize in Physics in 1903. [2] Nobel Prize | Awards are given in Physics, Chemistry, and Medicine.\n"
                    "Analysis: Passages confirm one prize and multiple fields, but don't link Marie Curie to Chemistry.\n"
                    "Missing: Confirmation that her second prize was in Chemistry.\n"
                    "Query: 'Marie Curie Nobel Prize in Chemistry'"
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
                "aim": "Verify claim completeness and generate final verification query",
                "stage_action": (
                    "Review the claim and ALL retrieved passages to determine if full verification exists. "
                    "If gaps remain, formulate a query targeting official confirmation sources. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "Is there any aspect lacking direct evidence? What authoritative source could confirm this?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | ... 1903 Physics ... [2] ... [3] Marie Curie | ... Nobel Prize in Chemistry 1911 ...\n"
                    "Analysis: Passages confirm both prizes but lack official records listing both awards.\n"
                    "Missing: Nobel Prize committee's official documentation of dual awards.\n"
                    "Query: 'Nobel Prize official laureates list Marie Curie'"
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