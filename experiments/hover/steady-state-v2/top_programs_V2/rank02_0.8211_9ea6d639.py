def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your task is to verify claims by retrieving supporting evidence from Wikipedia. Decompose the claim into atomic factual components. At each step, carefully analyze the provided evidence to identify which components are verified (only if explicitly stated) and which are missing. Generate precise search queries to fill critical gaps. When generating multiple queries for the same hop, ensure they target distinct aspects. Be skeptical: treat evidence as insufficient if it is ambiguous or indirect.",
        "steps": [
            # Step 1: First-hop deep retrieval
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Structured gap analysis with claim decomposition
            {
                "number": 2,
                "title": "Decompose claim and identify critical gaps",
                "step_type": "llm",
                "aim": "Decompose the claim into key factual components and identify verified facts and critical gaps",
                "stage_action": (
                    "Break the claim into its essential factual components (subject, action, object, qualifiers). "
                    "For each component, check if the retrieved evidence explicitly verifies it. "
                    "Be skeptical: if the evidence is ambiguous, indirect, or does not directly address the component, treat it as unverified. "
                    "List up to 3 critical gaps (unverified components) that are essential for claim verification, one per line. "
                    "If there are fewer than 3 gaps, leave the remaining lines empty. Format: 'GAP 1: ...\nGAP 2: ...\nGAP 3: ...'"
                ),
                "reasoning_questions": (
                    "1. What are the key factual components of the claim?\n"
                    "2. For each component, does the evidence explicitly state it? (Be strict: no inference)\n"
                    "3. Which unverified components are most critical for verification?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes in different scientific fields.'\n"
                    "Retrieved: [1] Nobel Prize | Marie Curie was the first woman to win a Nobel Prize, and the only woman to win twice.\n"
                    "Decomposition:\n"
                    "  - Subject: Marie Curie -> verified (explicitly mentioned)\n"
                    "  - Action: won -> verified\n"
                    "  - Object: two Nobel Prizes -> verified (evidence states 'win twice')\n"
                    "  - Qualifier: in different scientific fields -> unverified (evidence doesn't specify fields)\n"
                    "Critical gaps:\n"
                    "GAP 1: The scientific fields of Marie Curie's Nobel Prizes.\n"
                    "GAP 2: \n"
                    "GAP 3: "
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for first gap
            {
                "number": 3,
                "title": "Generate query for gap 1",
                "step_type": "llm",
                "aim": "Generate a search query for the first critical gap",
                "stage_action": (
                    "If GAP 1 (from step 2) is non-empty, generate a precise search query (3-5 terms) targeting ONLY the missing fact in GAP 1. "
                    "If GAP 1 is empty, output 'SKIP'. "
                    "Provide ONLY the search query text or 'SKIP' with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. Is GAP 1 specified?\n"
                    "2. What is the core missing fact in GAP 1?\n"
                    "3. How to phrase this as a concise 3-5 term query?"
                ),
                "example_reasoning": (
                    "GAP 1: The scientific fields of Marie Curie's Nobel Prizes.\n"
                    "Query: 'Marie Curie Nobel Prize fields'"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate query for second gap
            {
                "number": 4,
                "title": "Generate query for gap 2",
                "step_type": "llm",
                "aim": "Generate a search query for the second critical gap",
                "stage_action": (
                    "If GAP 2 (from step 2) is non-empty, generate a precise search query (3-5 terms) targeting ONLY the missing fact in GAP 2. "
                    "If GAP 2 is empty, output 'SKIP'. "
                    "Provide ONLY the search query text or 'SKIP' with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. Is GAP 2 specified?\n"
                    "2. What is the core missing fact in GAP 2?\n"
                    "3. How to phrase this as a concise 3-5 term query?"
                ),
                "example_reasoning": (
                    "GAP 2: The years Marie Curie won her Nobel Prizes.\n"
                    "Query: 'Marie Curie Nobel Prize years'"
                ),
                "dependencies": [2],
            },
            # Step 5: Generate query for third gap
            {
                "number": 5,
                "title": "Generate query for gap 3",
                "step_type": "llm",
                "aim": "Generate a search query for the third critical gap",
                "stage_action": (
                    "If GAP 3 (from step 2) is non-empty, generate a precise search query (3-5 terms) targeting ONLY the missing fact in GAP 3. "
                    "If GAP 3 is empty, output 'SKIP'. "
                    "Provide ONLY the search query text or 'SKIP' with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. Is GAP 3 specified?\n"
                    "2. What is the core missing fact in GAP 3?\n"
                    "3. How to phrase this as a concise 3-5 term query?"
                ),
                "example_reasoning": (
                    "GAP 3: Confirmation that the scientific fields are different.\n"
                    "Query: 'Physics Chemistry different fields'"
                ),
                "dependencies": [2],
            },
            # Step 6: Retrieve for query 1
            {
                "number": 6,
                "title": "Retrieve passages for query 1",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 7: Retrieve for query 2
            {
                "number": 7,
                "title": "Retrieve passages for query 2",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 8: Retrieve for query 3
            {
                "number": 8,
                "title": "Retrieve passages for query 3",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            # Step 9: Final gap analysis and third-hop query generation
            {
                "number": 9,
                "title": "Synthesize evidence and generate final query",
                "step_type": "llm",
                "aim": "Synthesize all evidence and generate a query for the most critical remaining gap (if any)",
                "stage_action": (
                    "Review all evidence from first and second hops. Break the claim into key factual components. "
                    "For each component, state whether it is verified (only if evidence explicitly states it; be skeptical of ambiguity). "
                    "If all components are verified, output 'NO_GAPS'. "
                    "Otherwise, identify the single most critical unverified component and output ONLY a search query (3-5 terms) targeting that component. "
                    "Do not output anything else."
                ),
                "reasoning_questions": (
                    "1. What new facts have been verified by the second-hop evidence?\n"
                    "2. What critical details remain unverified?\n"
                    "3. Which unverified component is most critical for the claim?"
                ),
                "example_reasoning": (
                    "Initial claim: 'Marie Curie won two Nobel Prizes in different scientific fields.'\n"
                    "First-hop evidence: [1] Nobel Prize | Marie Curie won the Nobel Prize in Physics in 1903.\n"
                    "Second-hop evidence for GAP1: [1] Chemistry | She won her second Nobel Prize in Chemistry in 1911.\n"
                    "Decomposition:\n"
                    "  - Subject: Marie Curie -> verified\n"
                    "  - Action: won -> verified\n"
                    "  - Object: two Nobel Prizes -> verified (1903 and 1911)\n"
                    "  - Qualifier: different scientific fields -> unverified (evidence states Physics and Chemistry but doesn't explicitly say they are different fields)\n"
                    "Most critical gap: That Physics and Chemistry are different scientific fields.\n"
                    "Query: 'Physics Chemistry different fields'"
                ),
                "dependencies": [2, 6, 7, 8],
            },
            # Step 10: Final retrieval
            {
                "number": 10,
                "title": "Retrieve final passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }