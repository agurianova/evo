def entrypoint():
    return {
        "system_prompt": (
            "You are a meticulous fact-checker verifying claims using multi-hop evidence retrieval. "
            "Your goal is to retrieve all relevant evidence to verify the claim by performing necessary retrieval hops. "
            "When generating a search query, output ONLY the query string with no additional text. "
            "When summarizing evidence, be concise and factual, focusing on information directly relevant to the claim."
        ),
        "steps": [
            # Step 1: First-hop retrieval
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "1. What is the main subject of the claim?\n"
                    "2. Which facts in the retrieved passages directly relate to the claim?\n"
                    "3. Are there any contradictions in the evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages:\n"
                    "  [1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "Summary: The Eiffel Tower construction started in 1887 and finished in 1889."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific information is missing from the first-hop evidence to verify the claim?\n"
                    "2. What entities or events should be searched for to find the missing information?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Summary: The Eiffel Tower construction started in 1887 and finished in 1889.\n"
                    "Missing: The exact year of the start of construction is stated as 1887, but we need to confirm if that is the year the foundation was laid or the year construction officially began.\n"
                    "Query: 'Eiffel Tower construction start date'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence (new step to avoid dilution)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "1. Which facts in these passages address the missing information from the first hop?\n"
                    "2. Do these passages provide new evidence or confirm existing evidence?\n"
                    "3. Are there any contradictions with the first-hop evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop summary: Construction started in 1887 and finished in 1889.\n"
                    "Retrieved passages:\n"
                    "  [1] Gustave Eiffel | In 1887, Eiffel signed the contract and began construction.\n"
                    "Summary: Gustave Eiffel signed the construction contract in 1887, confirming the start year."
                ),
                "dependencies": [4],
            },
            # Step 6: Integrate evidence and analyze gaps (replaces original step5 and step6)
            {
                "number": 6,
                "title": "Integrate evidence and analyze gaps",
                "step_type": "llm",
                "aim": "Combine evidence from both hops and determine if additional evidence is needed.",
                "stage_action": (
                    "Read the first-hop evidence summary and the second-hop evidence summary. Then, answer:\n"
                    "- What facts have been established?\n"
                    "- What specific information is still missing to verify the claim?\n"
                    "If there are missing facts, write a concise search query to find the missing evidence.\n"
                    "If the evidence is sufficient, output exactly: 'NO_HOP_NEEDED'.\n"
                    "Do not output any other text."
                ),
                "reasoning_questions": (
                    "1. What key facts are present in the first-hop summary?\n"
                    "2. What key facts are present in the second-hop summary?\n"
                    "3. What specific fact is missing to verify the claim? (If none, state 'None')"
                ),
                "example_reasoning": (
                    "Example 1 (needs third hop):\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  First-hop summary: Construction started in 1887 and finished in 1889.\n"
                    "  Second-hop summary: Gustave Eiffel signed the construction contract in 1887.\n"
                    "  Analysis: The contract signing in 1887 does not confirm the actual start of construction. We need the date when building work began.\n"
                    "  Query: 'Eiffel Tower actual construction start date'\n\n"
                    "Example 2 (sufficient evidence):\n"
                    "  Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "  First-hop summary: Construction started in 1887 and finished in 1889.\n"
                    "  Second-hop summary: Building work on the Eiffel Tower commenced in February 1887.\n"
                    "  Analysis: The evidence confirms construction began in 1887.\n"
                    "  NO_HOP_NEEDED"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (conditional)
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