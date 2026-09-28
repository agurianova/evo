def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims using multi-hop evidence retrieval. When generating search queries, output ONLY the query string with no additional text. When summarizing evidence, be concise and focus on facts directly relevant to the claim.",
        "steps": [
            # Step 1: First-hop retrieval (upgraded to deep)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
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
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
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
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The Great Wall of China is visible from space.'\n"
                    "First-hop summary: The Great Wall is a series of fortifications. Astronauts report it's hard to see without aid.\n"
                    "Missing: Official statements from space agencies.\n"
                    "Query: 'Great Wall of China visible from space official statement'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (now depends on first and second hop summaries)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary and second-hop evidence summary, "
                    "determine what final piece of evidence is needed to fully verify the claim. "
                    "Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The Great Wall of China is visible from space.'\n"
                    "First-hop summary: The Great Wall is a series of fortifications. Astronauts report it's hard to see without aid.\n"
                    "Second-hop summary: NASA states the Great Wall is generally not visible to the naked eye from space.\n"
                    "Missing: Confirmation if any astronaut has ever seen it without aid.\n"
                    "Query: 'Great Wall of China visible from space astronaut account'"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (deep)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence (new step to address evidence_summarization_gap)
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            # Step 9: Gap analysis with NO_QUERY example (fixed example_deficiency)
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query generation",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient or generate next query",
                "stage_action": (
                    "Review the first-hop evidence summary, second-hop evidence summary, and third-hop evidence summary. "
                    "If there is a gap in the evidence that prevents full verification of the claim, output ONLY the search query for the missing evidence. "
                    "If the evidence is sufficient, output 'NO_QUERY'."
                ),
                "reasoning_questions": "What key facts are still missing? What query would best capture the missing information?",
                "example_reasoning": (
                    "Example 1 (with gap):\n"
                    "Claim: 'Albert Einstein won the Nobel Prize in Physics in 1921.'\n"
                    "First-hop summary: Einstein won the Nobel Prize in Physics for his work on the photoelectric effect.\n"
                    "Second-hop summary: The Nobel Prize was awarded to Einstein in 1922.\n"
                    "Third-hop summary: The 1921 Nobel Prize in Physics was awarded to Einstein in 1922 due to committee delays.\n"
                    "Analysis: The claim states 1921 as the award year, but the prize was awarded in 1922. We need to confirm the official award year designation.\n"
                    "Query: 'Einstein Nobel Prize award year designation'\n\n"
                    "Example 2 (without gap):\n"
                    "Claim: 'Water boils at 100 degrees Celsius at sea level.'\n"
                    "First-hop summary: Water's boiling point is 100°C at standard atmospheric pressure.\n"
                    "Second-hop summary: Sea level atmospheric pressure is defined as 1 atmosphere.\n"
                    "Third-hop summary: Scientific sources consistently state water boils at 100°C at 1 atm pressure.\n"
                    "Analysis: All evidence confirms the claim without contradiction. No missing information.\n"
                    "Query: NO_QUERY"
                ),
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deep)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }