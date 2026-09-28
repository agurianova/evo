def entrypoint():
    return {
        "system_prompt": "Evidence retrieval assistant for claim verification. Be precise. Steps 3 and 6: output ONLY the search query string.",
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
                "aim": "Extract key facts including entities, dates, numerical values, and critical relationships from retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and extract all key facts relevant to verifying the claim, "
                    "including entities, dates, numerical values, and critical relationships (e.g., chemical equations, causal links). "
                    "Summarize evidence by listing structured facts. Explicitly state missing information under 'Missing:' header."
                ),
                "reasoning_questions": (
                    "What key facts (entities, dates, numbers, relationships) are present? "
                    "What critical information is still missing? List missing items specifically under 'Missing:'"
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "Retrieved passages: [Tokyo is capital of Japan; Japan population 126M in 2020]. "
                    "Relevant facts: [Capital: Tokyo, Country: Japan, Population of Japan: 126 million (2020)]. "
                    "Missing: population of Tokyo in 2020."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate optimal search query for second hop.",
                "stage_action": (
                    "Based on evidence summary, determine the most critical missing piece of information. "
                    "Write a concise search query to find that information. Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "What specific fact (entity, date, number, relationship) is missing? "
                    "Generate 2-3 alternative search queries. Evaluate which is most precise for retrieval. "
                    "Choose the best query."
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "Evidence summary: [Capital: Tokyo, Country: Japan, Population of Japan: 126M (2020)]. "
                    "Missing: Tokyo population 2020. "
                    "Query variations: 'Tokyo population 2020', 'Tokyo city population 2020 official', '2020 Tokyo census'. "
                    "Best query: 'Tokyo population 2020 official'"
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
                "aim": "Combine evidence hops into structured facts with explicit gap reporting.",
                "stage_action": (
                    "Integrate first-hop summary and second-hop passages. Extract all key facts (entities, dates, numbers, relationships) "
                    "relevant to the claim. Explicitly state remaining gaps under 'Missing:' header."
                ),
                "reasoning_questions": (
                    "What new facts (entities, dates, numbers, relationships) were found? "
                    "What critical information is still missing? List missing items under 'Missing:'"
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "First-hop: [Capital: Tokyo, Country: Japan, Population of Japan: 126M (2020)]. "
                    "Second-hop: [Tokyo metro population: 37.4M (2019)]. "
                    "Relevant facts: [Capital: Tokyo, Country: Japan, Population of Japan: 126M (2020), Tokyo metro population: 37.4M (2019)]. "
                    "Missing: population of Tokyo city proper in 2020."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final missing evidence and generate optimal query for third hop.",
                "stage_action": (
                    "This is the last retrieval step. Determine the single most critical missing fact. "
                    "Write a concise search query to find it. Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "What is the one critical fact (entity, date, number, relationship) still missing? "
                    "Generate 2-3 alternative search queries. Evaluate which is most precise for final retrieval. "
                    "Choose the best query."
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "Integrated evidence: [Capital: Tokyo, Country: Japan, Population of Japan: 126M (2020), Tokyo metro population: 37.4M (2019)]. "
                    "Missing: population of Tokyo city proper in 2020. "
                    "Query variations: 'Tokyo city population 2020', 'Tokyo official population 2020', '2020 Tokyo city census'. "
                    "Best query: 'Tokyo city population 2020 official'"
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
