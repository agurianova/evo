def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to maximize retrieval coverage of supporting evidence by conducting thorough multi-hop searches. Always aim to find all relevant documents for claim verification.",
        "steps": [
            # Step 1: First-hop retrieval (deep)
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
                "reasoning_questions": (
                    "1. What specific facts from the passages directly support or refute the claim?\n"
                    "2. Are there any entities, dates, or events mentioned that are crucial to the claim?\n"
                    "3. What information is still missing to fully verify the claim?"
                ),
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
                    "Example reasoning:\n"
                    "The claim is about the cause of the French Revolution. The first-hop passages mention economic hardship and Enlightenment ideas, but do not specify the role of the Estates-General. The missing information is the immediate trigger event. Therefore, the query should be: 'Estates-General French Revolution trigger'"
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
            # Step 5: Summarize first and second hop evidence
            {
                "number": 5,
                "title": "Combine first and second hop evidence",
                "step_type": "llm",
                "aim": "Integrate evidence from first and second hops into a unified summary.",
                "stage_action": (
                    "Merge the first-hop evidence summary with the second-hop passages. "
                    "Produce a comprehensive summary covering all relevant facts found so far."
                ),
                "reasoning_questions": (
                    "1. How does the new evidence from the second hop complement or contradict the first-hop evidence?\n"
                    "2. What key elements of the claim are now verified, and what remains unverified?\n"
                    "3. What specific gap in evidence should be targeted next?"
                ),
                "example_reasoning": "<none>",
                "dependencies": [2, 4],
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
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "The claim states that Marie Curie won two Nobel Prizes in different sciences. The first two hops confirm she won in Physics and Chemistry, but do not specify the years. The missing information is the exact years to verify the timeline. Query: 'Marie Curie Nobel Prizes years'"
                ),
                "dependencies": [5],
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
            # Step 8: Summarize all evidence (first, second, third hop)
            {
                "number": 8,
                "title": "Combine all evidence so far",
                "step_type": "llm",
                "aim": "Create a comprehensive summary integrating evidence from all three hops.",
                "stage_action": (
                    "Synthesize the combined evidence from steps 5 (first and second hop) and "
                    "the third-hop passages. Produce a unified summary covering all verified "
                    "facts and remaining gaps."
                ),
                "reasoning_questions": (
                    "1. What new information does the third hop provide?\n"
                    "2. Which parts of the claim are now fully verified?\n"
                    "3. What is the most critical remaining evidence gap?"
                ),
                "example_reasoning": "<none>",
                "dependencies": [5, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical remaining evidence gap and generate a targeted search query.",
                "stage_action": (
                    "Based on the complete evidence summary, determine the single most important "
                    "piece of evidence still missing. Write a concise search query to find "
                    "this evidence.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example reasoning:\n"
                    "The claim is about the health effects of coffee. The first three hops cover cardiovascular and cancer risks, but do not address neurological effects like Parkinson's disease. The critical remaining gap is neurological benefits. Query: 'coffee Parkinson's disease prevention'"
                ),
                "dependencies": [8],
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
