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
            # Step 6: Generate third-hop query (updated dependencies)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far (first-hop and second-hop summaries), "
                    "determine what final piece of evidence is needed to fully verify the claim. "
                    "Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Claim: 'The Great Wall of China is visible from space.'\n"
                    "First-hop summary: The Great Wall is a series of fortifications.\n"
                    "Second-hop summary: NASA states it's generally not visible to the naked eye.\n"
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
            # Step 8: Summarize third-hop evidence (new step)
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            # Step 9: Gap analysis and fourth-hop query generation (updated dependencies and example)
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query generation",
                "step_type": "llm",
                "aim": "Determine if the evidence gathered so far is sufficient to verify the claim. If not, generate a search query for the next hop.",
                "stage_action": (
                    "Review the evidence summaries from the first hop (step2), second hop (step5), and third hop (step8). "
                    "If there is a gap in the evidence that prevents full verification of the claim, output ONLY the search query for the missing evidence. "
                    "If the evidence is sufficient, output 'NO_QUERY'."
                ),
                "reasoning_questions": "What key facts are still missing? What query would best capture the missing information?",
                "example_reasoning": (
                    "Example 1 (needs more evidence):\n"
                    "The claim is: 'Albert Einstein won the Nobel Prize in Physics in 1921.'\n"
                    "First-hop summary: Einstein won the Nobel Prize in Physics for his work on the photoelectric effect.\n"
                    "Second-hop summary: The prize was awarded in 1922.\n"
                    "Third-hop summary: The Nobel Foundation confirms the 1921 prize was awarded in 1922.\n"
                    "Analysis: The claim states 1921 as the award year, but evidence shows it was awarded in 1922. We need to confirm the official award year to verify the claim.\n"
                    "Query: 'Einstein Nobel Prize official award year'\n\n"
                    "Example 2 (evidence sufficient):\n"
                    "The claim is: 'The Great Wall of China is visible from space.'\n"
                    "First-hop summary: The Great Wall is a series of fortifications.\n"
                    "Second-hop summary: NASA states it's generally not visible to the naked eye.\n"
                    "Third-hop summary: Astronauts confirm it is difficult to see without magnification.\n"
                    "Analysis: The evidence consistently states the Great Wall is not visible to the naked eye from space, which directly contradicts the claim. No further evidence needed.\n"
                    "NO_QUERY"
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