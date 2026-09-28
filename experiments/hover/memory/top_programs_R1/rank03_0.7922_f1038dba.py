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
                "aim": "Identify compound gaps across first+second-hop evidence and generate precise search query",
                "stage_action": (
                    "Synthesize all retrieved passages to identify missing relationships between entities. "
                    "Formulate a concise search query targeting compound gaps. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks support? What relationships between entities across the first and second hop evidence are missing?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages from first hop: [1] Marie Curie | She won the Nobel Prize in Physics in 1903.\n"
                    "Passages from second hop: [2] Nobel Prize in Chemistry | Several scientists have won in multiple fields, including Marie Curie.\n"
                    "Analysis: First hop confirms Physics prize. Second hop mentions Chemistry but doesn't explicitly state Marie Curie won it.\n"
                    "Missing: Direct confirmation that Marie Curie won the Nobel Prize in Chemistry and the year.\n"
                    "Query: 'Marie Curie Nobel Prize in Chemistry year'"
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
                "aim": "Identify final verification gaps across all evidence and generate precise search query",
                "stage_action": (
                    "Review all retrieved passages to identify any remaining verification gaps. "
                    "Formulate a concise search query targeting official confirmation. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "After reviewing all evidence, what specific detail is still missing to fully verify the claim? Is there any inconsistency or lack of official confirmation?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages from first hop: [1] Marie Curie | She won the Nobel Prize in Physics in 1903.\n"
                    "Passages from second hop: [2] Nobel Prize in Chemistry | Several scientists have won in multiple fields, including Marie Curie.\n"
                    "Passages from third hop: [3] Marie Curie Chemistry Prize | She was awarded the Nobel Prize in Chemistry in 1911.\n"
                    "Analysis: Evidence confirms two prizes but lacks an official source listing both together.\n"
                    "Missing: Official Nobel Prize record explicitly stating Marie Curie won two prizes.\n"
                    "Query: 'Official Nobel Prize list Marie Curie two prizes'"
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