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
                "aim": "Synthesize first and second-hop evidence to identify compound gaps and generate precise search query for third hop",
                "stage_action": (
                    "Analyze the claim and ALL retrieved passages (from first and second hops) to determine missing compound evidence. "
                    "Focus on relationships between entities that require information from multiple passages. "
                    "Formulate a concise search query targeting the gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key relationship between entities in the claim lacks support? Which compound fact (requiring multiple hops) is missing?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in different fields.'\n"
                    "Passages from first hop: [1] Marie Curie | She won the Nobel Prize in Physics in 1903.\n"
                    "Passages from second hop: [2] Nobel Prize in Chemistry | Awarded for discovery of radium and polonium.\n"
                    "Analysis: Passages confirm Physics prize and Chemistry prize existence but do not link Marie Curie to the Chemistry prize.\n"
                    "Missing: Explicit statement that Marie Curie won the Chemistry prize.\n"
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
                "aim": "Synthesize all evidence to identify subtle gaps and generate final search query for fourth hop",
                "stage_action": (
                    "Analyze the claim and ALL retrieved passages (from first, second, and third hops) to determine the most subtle missing evidence. "
                    "Focus on verification details (e.g., official sources, exact dates, or cross-references). "
                    "Formulate a concise search query targeting the gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What verification detail (e.g., official record, exact date, or authoritative source) is still missing? Is there any ambiguity left?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in different fields.'\n"
                    "Passages: [1] Marie Curie | ... Physics ... [2] ... Chemistry ... [3] Marie Curie biography | She remains the only person to win Nobel Prizes in two different sciences.\n"
                    "Analysis: Passages confirm two prizes in different fields but lack official Nobel Prize committee records for verification.\n"
                    "Missing: Official citation from Nobel Prize organization confirming both awards.\n"
                    "Query: 'Nobel Prize official announcement Marie Curie two prizes'"
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