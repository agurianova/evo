def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. At each step, focus on identifying the most relevant evidence and gaps. Success is measured by the fraction of gold supporting documents retrieved.",
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
                    "Example reasoning: The first-hop summary indicates that the claim is about the birth year of Albert Einstein. "
                    "The missing information is the exact birth year. Therefore, the search query should be: 'Albert Einstein birth year'"
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
            # Step 5: Unified evidence summary with gap analysis
            {
                "number": 5,
                "title": "Generate unified evidence summary",
                "step_type": "llm",
                "aim": "Combine raw evidence from first and second hops into a comprehensive summary and identify remaining gaps.",
                "stage_action": (
                    "Integrate the raw passages from the first-hop (step1) and second-hop (step4). "
                    "Produce a unified evidence summary covering all relevant facts found so far. "
                    "Additionally, list explicitly any missing evidence required to fully verify the claim. "
                    "Structure the output as:\n"
                    "Summary: <summary>\n"
                    "Missing evidence: <list of missing evidence items>"
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example reasoning: \n"
                    "Summary: Albert Einstein was born in Ulm, Germany. He published the theory of special relativity in 1905. "
                    "However, the claim also requires the exact date of the publication of the general theory of relativity.\n"
                    "Missing evidence: publication date of general theory of relativity"
                ),
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the 'Missing evidence' list from the unified summary (step5), "
                    "write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example reasoning: The unified summary states that the missing evidence is the publication date of the theory of relativity. "
                    "Therefore, the search query should be: 'theory of relativity publication date'"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval (deeper search)
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
        ],
    }
