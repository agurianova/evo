def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your task is to verify claims by retrieving supporting evidence from Wikipedia. At each step, carefully analyze and summarize retrieved evidence to identify specific missing facts, then generate concise search queries (2-4 terms) targeting the most critical gaps.",
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
            # Step 2: Summarize first-hop evidence and identify gaps
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Distill critical evidence and identify gaps from first-hop passages",
                "stage_action": (
                    "Review the retrieved passages and output a structured summary in the format:\n"
                    "Known: [list of verified facts]\n"
                    "Missing: [list of specific missing facts]\n"
                    "Focus ONLY on facts directly relevant to verifying the claim."
                ),
                "reasoning_questions": (
                    "1. What key facts from the claim are confirmed by these passages?\n"
                    "2. What specific details remain unverified?\n"
                    "3. Which missing fact is most critical for verification?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes in different scientific fields.'\n"
                    "Passages: [1] Nobel Prize | ... [2] Physics | ...\n"
                    "Known: Marie Curie won Nobel Prizes.\n"
                    "Missing: The two different scientific fields and the years."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate concise search query for most critical missing fact",
                "stage_action": (
                    "Based on the 'Missing' list from the summary, select the SINGLE most critical missing fact.\n"
                    "Formulate a search query of 2-4 terms that targets ONLY this fact.\n"
                    "Output ONLY the query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. Which missing fact is essential for verification?\n"
                    "2. How can we phrase this as a minimal, precise query?\n"
                    "3. Will this query likely retrieve passages about this specific fact?"
                ),
                "example_reasoning": (
                    "Summary: Known: Marie Curie won Nobel Prizes. Missing: The two different scientific fields and the years.\n"
                    "Critical gap: scientific fields\n"
                    "Query: 'Marie Curie Nobel Prize fields'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop deep retrieval
            {
                "number": 4,
                "title": "Retrieve second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize all evidence and update gaps
            {
                "number": 5,
                "title": "Synthesize evidence and update gaps",
                "step_type": "llm",
                "aim": "Combine evidence from all hops and identify remaining gaps",
                "stage_action": (
                    "Merge the first-hop summary and new second-hop passages to create an updated structured summary:\n"
                    "Known: [updated verified facts]\n"
                    "Missing: [remaining unverified facts]\n"
                    "Prioritize gaps that are still unverified."
                ),
                "reasoning_questions": (
                    "1. What new facts are confirmed by the second-hop passages?\n"
                    "2. Which previously missing facts are now verified?\n"
                    "3. What critical gaps remain?"
                ),
                "example_reasoning": (
                    "First summary: Known: Marie Curie won Nobel Prizes. Missing: fields and years.\n"
                    "Second-hop: [1] Chemistry | ... [2] Physics | ...\n"
                    "Known: Marie Curie won Nobel Prizes in Physics and Chemistry.\n"
                    "Missing: The years of each prize."
                ),
                "dependencies": [2, 4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate concise search query for final critical gap",
                "stage_action": (
                    "Select the SINGLE most critical remaining gap from the updated 'Missing' list.\n"
                    "Formulate a 2-4 term query targeting this gap.\n"
                    "Output ONLY the query text with no additional commentary."
                ),
                "reasoning_questions": (
                    "1. What is the most important remaining unverified detail?\n"
                    "2. How can we phrase the query to be minimal and precise?\n"
                    "3. Will this query avoid irrelevant results?"
                ),
                "example_reasoning": (
                    "Summary: Known: Marie Curie won Nobel Prizes in Physics and Chemistry. Missing: years.\n"
                    "Critical gap: years\n"
                    "Query: 'Marie Curie Nobel Prize years'"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop deep retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }