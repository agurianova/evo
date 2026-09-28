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
            # Step 3: Generate second-hop query (enhanced with reasoning scaffolds)
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
                "reasoning_questions": "What specific fact is missing to verify the claim? What entities or relationships should the next query focus on?",
                "example_reasoning": "The claim states 'X'. The first-hop passages mention Y but do not address Z. Therefore, the missing fact is about Z. A good query would be 'Z and [claim subject]'.",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deeper search)
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
            # Step 5: Summarize evidence using raw passages (improved fidelity)
            {
                "number": 5,
                "title": "Summarize first and second-hop evidence",
                "step_type": "llm",
                "aim": "Combine raw evidence from first and second hops into comprehensive summary",
                "stage_action": (
                    "Integrate the first-hop raw passages (step1) with the second-hop passages (step4). "
                    "Produce a unified evidence summary covering all relevant facts found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query (enhanced with reasoning scaffolds)
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
                "reasoning_questions": "Given all evidence so far, what is the one critical fact still missing? How can we phrase a query to target that fact?",
                "example_reasoning": "We have evidence about A and B, but the claim requires confirmation of C. The next query should be 'C [claim subject]'.",
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
                "title": "Analyze gaps after three hops",
                "step_type": "llm",
                "aim": "Identify remaining gaps after three hops of evidence collection",
                "stage_action": (
                    "Review all evidence collected in the first three retrieval steps (steps 1, 4, and 7). "
                    "Determine if there is still missing evidence that prevents full verification of the claim. "
                    "List the specific gaps."
                ),
                "reasoning_questions": "What critical fact is still missing? Which part of the claim remains unverified? Are there any contradictions or ambiguities in the current evidence?",
                "example_reasoning": "The claim requires evidence of event X occurring in year Y. Passages from step1 confirm event X but not the year. Step4 provides context about year Y but not event X. Step7 gives a source that mentions both but without clear connection. The gap is a direct link between event X and year Y.",
                "dependencies": [1, 4, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a search query for the fourth hop based on identified gaps",
                "stage_action": (
                    "Write a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? How can we phrase a query to target that fact without being too broad?",
                "example_reasoning": "The gap is a direct link between event X and year Y. A good query would be 'event X year Y confirmation' or 'event X occurred in year Y source'.",
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
