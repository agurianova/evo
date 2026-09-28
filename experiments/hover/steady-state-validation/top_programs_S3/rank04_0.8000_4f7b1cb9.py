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
            # Step 2: Summarize first-hop evidence (unused but retained for structural consistency)
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
            # Step 3: Generate second-hop query with enhanced scaffolding
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
                "reasoning_questions": "What specific fact is missing from the first-hop evidence that would help verify the claim? How can we phrase a search query to find that fact?",
                "example_reasoning": "The claim states 'X'. The first-hop evidence shows Y but does not address Z. We need evidence about Z. A good query would be: 'Z and [related terms]'",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval with deeper search
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
            # Step 5: Summarize evidence from first two hops using raw passages
            {
                "number": 5,
                "title": "Summarize first and second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Read the raw first-hop passages (step1) and the raw second-hop passages (step4). "
                    "Identify all facts relevant to verifying the claim. Produce a comprehensive evidence "
                    "summary that covers all relevant information found in both hops."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query with enhanced scaffolding
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
                "reasoning_questions": "Given the evidence from the first two hops, what specific fact is still missing to verify the claim? How can we phrase a query to find it?",
                "example_reasoning": "The claim requires proof of 'A'. The evidence so far covers B and C but not A. We need a document that states A. A good query: 'A proven by scientific study'",
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
            # Step 8: Gap analysis after three hops
            {
                "number": 8,
                "title": "Analyze evidence gaps after three hops",
                "step_type": "llm",
                "aim": "Identify specific missing evidence after three hops of retrieval",
                "stage_action": (
                    "Read the comprehensive evidence summary from the first two hops (step5) and the "
                    "third-hop retrieved passages (step7). Determine what specific facts are still missing "
                    "to fully verify the claim. Be precise about the gap."
                ),
                "reasoning_questions": "What key aspect of the claim remains unverified? What specific fact or document would resolve this? How can we search for it?",
                "example_reasoning": "The claim requires evidence about 'X'. The evidence so far covers A and B but not C. We need a document that states C explicitly. A good gap description is: 'Evidence that X causes C'",
                "dependencies": [5, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a search query to find the missing evidence identified in step8",
                "stage_action": (
                    "Based on the gap analysis, write a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific terms should be included in the query to find the missing fact? How can we avoid ambiguity?",
                "example_reasoning": "Gap: 'Evidence that X causes C'. Query: 'X causes C scientific evidence'",
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
