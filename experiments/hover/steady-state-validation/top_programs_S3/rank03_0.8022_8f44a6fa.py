def entrypoint():
    return {
        "system_prompt": "",
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
                "reasoning_questions": "What specific fact is missing after reviewing the first-hop evidence? How can the query be phrased to get the most relevant results for the missing fact?",
                "example_reasoning": "First-hop evidence shows that X is true. The claim also requires evidence for Y. Missing fact: how X leads to Y.\nQuery: 'X leads to Y'",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (upgraded to deep)
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
            # Step 5: Combine evidence from first two hops (using raw passages)
            {
                "number": 5,
                "title": "Summarize first and second-hop evidence",
                "step_type": "llm",
                "aim": "Combine evidence from first two hops into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop retrieved passages (step1) with the second-hop retrieved passages (step4). "
                    "Produce a unified evidence summary covering all relevant facts found so far. "
                    "Focus on facts directly relevant to verifying the claim."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is still missing after reviewing the combined evidence from the first two hops? How can the query be phrased to get the most relevant results for the missing fact?",
                "example_reasoning": "Combined evidence shows X and Y, but the claim requires evidence for Z. Missing fact: the connection between Y and Z.\nQuery: 'Y and Z connection'",
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
            # Step 8: Gap analysis after third hop
            {
                "number": 8,
                "title": "Analyze evidence gaps after third hop",
                "step_type": "llm",
                "aim": "Identify remaining gaps in evidence after three hops of retrieval.",
                "stage_action": (
                    "Review all retrieved passages from the first, second, and third hops. "
                    "Determine what specific information is still missing to verify the claim. "
                    "Be precise about the missing fact or context."
                ),
                "reasoning_questions": "What specific fact or context is still missing? Which part of the claim remains unverified? Are there any contradictions in the evidence that need resolution?",
                "example_reasoning": "The claim states that X. From the first hop, we found evidence about Y. From the second hop, we found evidence about Z. However, there is no evidence connecting Y and Z to X. We need a source that explicitly states the relationship between Y and Z in the context of X.",
                "dependencies": [1, 4, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a precise search query to find the missing evidence identified in the gap analysis.",
                "stage_action": (
                    "Based on the gap analysis, write a concise search query that targets the missing information. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What is the most specific fact needed? How can we phrase the query to get the most relevant results? Avoid broad terms.",
                "example_reasoning": "Missing evidence: the connection between Y and Z in the context of X.\nQuery: 'Y and Z relationship in context of X'",
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval
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
