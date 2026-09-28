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
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the first immediate missing evidence in first-hop passages",
                "stage_action": (
                    "If the claim is fully supported by the current evidence, output an empty string. Otherwise, "
                    "Analyze the claim and first-hop passages to determine the most obvious missing fact. "
                    "Formulate a concise but comprehensive search query (5-15 words) targeting this gap, "
                    "including essential entities, dates, and necessary qualifiers (e.g., 'official'). "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What key fact from the claim lacks direct support? Which specific entity or date needs verification?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'The 1906 San Francisco earthquake had a magnitude of 7.9.'\n"
                    "Passages: [1] 1906 San Francisco earthquake | It occurred on April 18, 1906.\n"
                    "Analysis: Passages confirm the date but omit the magnitude.\n"
                    "Missing: The exact magnitude of the earthquake.\n"
                    "7.9 magnitude San Francisco earthquake 1906"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify an alternative missing evidence path from first-hop passages",
                "stage_action": (
                    "If the claim is fully supported by the current evidence, output an empty string. Otherwise, "
                    "Analyze the claim and first-hop passages to determine a different obvious missing fact. "
                    "Avoid using the same entities or aspects as in the first second-hop query (step2). "
                    "Formulate a concise but comprehensive search query (5-15 words) targeting this gap, "
                    "including essential entities, dates, and necessary qualifiers (e.g., 'official'). "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What other relationship or fact in the claim lacks support? Which entity could be verified through a different angle?",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | She won the Nobel Prize in Physics in 1903.\n"
                    "Analysis: Passages confirm one prize but omit the second award.\n"
                    "Missing: Field and year of second Nobel Prize.\n"
                    "Marie Curie second Nobel Prize field year"
                ),
                "dependencies": [1, 2, 3],
            },
            {
                "number": 5,
                "title": "Retrieve second second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query (if needed)",
                "step_type": "llm",
                "aim": "Verify claim completeness by synthesizing evidence from all hops",
                "stage_action": (
                    "Review the claim and ALL retrieved passages to determine if full verification exists. "
                    "If gaps remain, explicitly list the missing elements (up to 3 key gaps). "
                    "Then, formulate a single concise but comprehensive search query (5-15 words) that targets the most critical gaps, "
                    "including essential entities, dates, and necessary qualifiers (e.g., 'official'). "
                    "If no gap exists, output an empty string. "
                    "Output exactly one line of text, no other content."
                ),
                "reasoning_questions": "What aspects lack direct evidence? Which authoritative sources could confirm these?",
                "example_reasoning": (
                    "Example reasoning 1 (no gap):\n"
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Passages: [1] Marie Curie | ... 1903 Physics ... [2] ... [3] Marie Curie | ... Nobel Prize in Chemistry 1911 ...\n"
                    "Analysis: Passages confirm both prizes with fields and years.\n"
                    "Missing: None.\n"
                    "\n"
                    "Example reasoning 2 (with gap):\n"
                    "Claim: 'The official cause of the Hindenburg disaster was an electrical spark.'\n"
                    "Passages: [1] Hindenburg disaster | It occurred on May 6, 1937. [2] ... [3] Hindenburg disaster | The disaster was caused by a fire.\n"
                    "Analysis: Passages confirm the date and fire cause but omit official determination and electrical spark evidence.\n"
                    "Missing: 1. Official cause from investigation report 2. Electrical spark verification\n"
                    "official Hindenburg disaster cause electrical spark investigation report"
                ),
                "dependencies": [1, 3, 5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }