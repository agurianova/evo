def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your task is to verify claims by retrieving supporting evidence from Wikipedia. At each step, carefully analyze retrieved passages to identify evidence gaps and generate precise search queries to fill them.",
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing evidence and generate precise search query for second hop",
                "stage_action": (
                    "Based on retrieved passages, determine what specific evidence is still needed to verify the claim. "
                    "Write a concise search query to find the missing information. "
                    "Provide ONLY the search query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What concrete fact is missing to fully support the claim?\n"
                    "2. Which entity or event should the next query target?\n"
                    "3. How can we phrase this to maximize relevant passage retrieval?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes in different scientific fields.'\n"
                    "Retrieved: [1] Nobel Prize | ... [2] Physics | ...\n"
                    "Missing: Specific fields of her Nobel Prizes and years.\n"
                    "Query: 'Marie Curie Nobel Prize fields years'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop deep retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining evidence gaps and generate precise search query for third hop",
                "stage_action": (
                    "Analyze all retrieved evidence so far to determine what specific information is still missing. "
                    "Write a concise search query targeting the remaining gap. "
                    "Provide ONLY the search query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What critical detail remains unverified?\n"
                    "2. Which aspect of the claim requires further substantiation?\n"
                    "3. How can we optimize this query for maximum recall of relevant passages?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919 and ended World War I.'\n"
                    "Retrieved: [1] World War I | ... [2] 1919 | ...\n"
                    "Missing: Specific signing date and participating nations.\n"
                    "Query: 'Treaty of Versailles signing date participating countries'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop deep retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gaps and generate precise search query for fourth hop",
                "stage_action": (
                    "Review all accumulated evidence to pinpoint any remaining verification gaps. "
                    "Formulate a targeted search query to obtain the missing information. "
                    "Provide ONLY the search query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What single piece of evidence would conclusively verify the claim?\n"
                    "2. Which specific detail remains unconfirmed by current evidence?\n"
                    "3. How can we phrase this query to avoid irrelevant results?"
                ),
                "example_reasoning": (
                    "Claim: 'Mount Everest's height is 8,848 meters above sea level.'\n"
                    "Retrieved: [1] Mount Everest | ... [2] 8,848 meters | ...\n"
                    "Missing: Official recognition year and measurement methodology.\n"
                    "Query: 'Mount Everest official height recognition year measurement method'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop deep retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
            # Step 8: Generate fifth-hop query
            {
                "number": 8,
                "title": "Generate fifth-hop query",
                "step_type": "llm",
                "aim": "Identify any residual evidence gaps and generate final search query",
                "stage_action": (
                    "Conduct final gap analysis across all evidence. "
                    "Create a precise search query for the last missing verification element. "
                    "Provide ONLY the search query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What minimal additional evidence would achieve full verification?\n"
                    "2. Which aspect of the claim lacks authoritative confirmation?\n"
                    "3. How can we optimize this final query for maximum precision?"
                ),
                "example_reasoning": (
                    "Claim: 'The human genome contains approximately 20,000 protein-coding genes.'\n"
                    "Retrieved: [1] Human genome | ... [2] 20,000 genes | ...\n"
                    "Missing: Most recent official count and research publication date.\n"
                    "Query: 'Human genome official protein-coding gene count latest publication'"
                ),
                "dependencies": [1, 3, 5, 7],
            },
            # Step 9: Fifth-hop deep retrieval
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }