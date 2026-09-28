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
                "aim": "Identify compound gaps in first+second-hop evidence and generate precise search query",
                "stage_action": (
                    "Synthesize the claim and all retrieved passages (from first and second hops) to identify missing relationships or compound facts. "
                    "Formulate a concise search query targeting the gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks support? What relationships between entities in the claim and retrieved evidence are missing?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in different scientific fields.'\n"
                    "First-hop passages:\n"
                    "[1] Marie Curie | ... won Nobel Prize in Physics (1903).\n"
                    "[2] Nobel Prize | Awards in Physics, Chemistry, Medicine, etc.\n"
                    "Second-hop passages (query: 'Marie Curie second Nobel Prize'):\n"
                    "[1] Nobel Prize in Chemistry | Marie Curie won in 1911.\n"
                    "[2] Multiple laureates | Curie won in two different sciences.\n"
                    "Analysis: Confirms two prizes in Physics and Chemistry, but lacks explicit statement that these are 'different scientific fields' as per the claim.\n"
                    "Missing: Official confirmation of the term 'scientific fields' for Nobel categories.\n"
                    "Query: 'Nobel Prize different scientific fields definition'"
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
                "aim": "Identify remaining gaps after three hops and generate final search query",
                "stage_action": (
                    "Synthesize the claim and all retrieved passages (from first, second, and third hops) to identify any remaining gaps. "
                    "Formulate a concise search query targeting the gap. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks support? What relationships between entities in the claim and retrieved evidence are missing?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in different scientific fields.'\n"
                    "First-hop: [1] ... [2] ...\n"
                    "Second-hop: [1] ... [2] ...\n"
                    "Third-hop (query: 'Nobel Prize different scientific fields definition'):\n"
                    "[1] Nobel Prize categories | The prizes are awarded in distinct scientific fields.\n"
                    "[2] History of Nobel Prize | The categories represent different branches of science.\n"
                    "Analysis: Passages confirm Physics and Chemistry are distinct fields, but lack explicit link to Marie Curie's prizes using claim terminology.\n"
                    "Missing: Source stating Marie Curie's prizes were in different scientific fields.\n"
                    "Query: 'Marie Curie Nobel Prizes different scientific fields official'"
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