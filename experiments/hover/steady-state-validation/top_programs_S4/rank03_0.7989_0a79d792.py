def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant for claim verification. Always follow instructions precisely. When asked to generate a search query, output ONLY the query string without any additional text, formatting, or explanations.",
        "steps": [
            # Step 1: First-hop retrieval (deep for better initial coverage)
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
                    "to verifying the claim. Summarize the most important evidence found "
                    "in a concise paragraph."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (with enhanced scaffolding)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is missing to verify the claim?\n"
                    "2. What are the key entities and relationships in the missing evidence?\n"
                    "3. What search terms would retrieve the missing evidence?"
                ),
                "example_reasoning": "effects of climate change on polar bear populations",
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
            # Step 5: Summarize second-hop evidence (fixes fragility)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found "
                    "in a concise paragraph."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (with enhanced scaffolding)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence summaries gathered so far, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is still missing to verify the claim?\n"
                    "2. How do the existing evidence summaries connect to the missing information?\n"
                    "3. What precise search terms would retrieve the final evidence?"
                ),
                "example_reasoning": "Arctic sea ice decline statistics 2023",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (deep for better recall)
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
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found "
                    "in a concise paragraph."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query (unconditional fourth hop)
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify any remaining gaps and generate a search query for the fourth hop.",
                "stage_action": (
                    "Based on all evidence summaries gathered so far, determine what additional evidence might still be needed to "
                    "fully verify the claim. Write a concise search query to find potential missing evidence.\n"
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. Is there any aspect of the claim not yet supported by evidence?\n"
                    "2. What alternative perspectives or data might exist?\n"
                    "3. What search terms would uncover supplementary evidence?"
                ),
                "example_reasoning": "peer-reviewed studies on polar bear population trends 2020-2023",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deep for maximum coverage)
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
