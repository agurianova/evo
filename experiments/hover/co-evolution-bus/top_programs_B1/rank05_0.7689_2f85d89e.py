def entrypoint():
    return {
        "system_prompt": "Expert fact-checker for multi-hop verification. Summarizers: claim-relevant facts only, output concise bullet points. Step 5 MUST end with 'Missing fact: [fact]' and nothing after. Query generators: pure query string only.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key entities and factual claims from retrieved passages relevant to the claim.",
                "stage_action": (
                    "List bullet points of key entities (people, places, dates) and verifiable facts. "
                    "Extract facts relevant to verifying the claim, including intermediate connections between entities. "
                    "Exclude opinions, irrelevant details, and potential noise."
                ),
                "reasoning_questions": (
                    "1. What are the main entities mentioned?\n"
                    "2. What specific facts (dates, numbers, events) are stated?\n"
                    "3. How do these facts connect to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'World War II began in 1938.'\n"
                    "Passages:\n"
                    "[1] World War II | Began on September 1, 1939, with the invasion of Poland.\n"
                    "Key entities: World War II\n"
                    "Facts: Began on September 1, 1939, with the invasion of Poland.\n"
                    "Relation: Claim states 1938, but passage says 1939."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing link to verify claim and generate focused search query.",
                "stage_action": (
                    "Based on the bullet-point summary, determine what specific information is missing. "
                    "Write a search query for the next required evidence. Include specific entities/dates and contextual qualifiers (e.g., 'construction completion year' not just 'completion year'). "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": (
                    "1. What key fact from the claim is unsupported by first-hop evidence?\n"
                    "2. What specific contextual qualifiers will target precise evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'World War II began in 1938.'\n"
                    "Summary:\n"
                    "- Entities: World War II\n"
                    "- Facts: Began on September 1, 1939, with the invasion of Poland.\n"
                    "World War II start date"
                ),
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into unified verification-focused summary.",
                "stage_action": (
                    "Integrate first-hop summary with second-hop passages. List bullet points of all key entities "
                    "and verifiable facts. For facts stated multiple times (even with different wording), merge them into a single statement "
                    "that preserves all unique attributes and details. Avoid listing the same fact more than once. "
                    "Then, state the most critical missing fact for verification in the format: 'Missing fact: [fact]' "
                    "as the final line of your output. DO NOT output any text after this line."
                ),
                "reasoning_questions": (
                    "1. What new entities/facts appear in second-hop passages?\n"
                    "2. How do these connect to first-hop evidence and claim?\n"
                    "3. What is the most critical fact still missing to confirm/refute the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Mount Everest is the tallest mountain.'\n"
                    "First-hop summary:\n"
                    "- Entities: Mount Everest\n"
                    "- Facts: Elevation 8,848 m above sea level.\n"
                    "Second-hop passages:\n"
                    "[1] Mauna Kea | Total height 10,210 m from base, but only 4,207 m above sea level.\n"
                    "[2] K2 | Elevation 8,611 m above sea level.\n"
                    "Unified summary:\n"
                    "- Entities: Mount Everest, Mauna Kea, K2\n"
                    "- Facts: Mount Everest: 8,848 m above sea level; Mauna Kea: total height 10,210 m (base to peak), but only 4,207 m above sea level; K2: 8,611 m above sea level.\n"
                    "Missing fact: the standard definition of 'tallest mountain' in geography (above sea level)"
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate precise query for the missing fact using evidence from prior steps.",
                "stage_action": (
                    "Using the 'Missing fact' statement from previous step, rephrase as search-optimized keywords "
                    "with specific contextual qualifiers (e.g., technical terms, specific attributes). "
                    "Include key entities, conditions, and technical terms from evidence. "
                    "Output ONLY the query string with no additional text, not even 'Query: '."
                ),
                "reasoning_questions": (
                    "1. What technical terms from the missing fact are most searchable?\n"
                    "2. Which specific attributes will best target the next required evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'Mount Everest is the tallest mountain.'\n"
                    "Unified summary:\n"
                    "- Entities: Mount Everest, Mauna Kea, K2\n"
                    "- Facts: Mount Everest: 8,848 m above sea level; Mauna Kea: total height 10,210 m (base to peak), but only 4,207 m above sea level; K2: 8,611 m above sea level.\n"
                    "Missing fact: the standard definition of 'tallest mountain' in geography (above sea level)\n"
                    "tallest mountain definition above sea level"
                ),
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
