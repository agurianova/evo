def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert. Retrieve all evidence needed to verify the claim. Focus on finding supporting documents by generating precise search queries and combining evidence from multiple sources.",
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
            # Step 2: Generate first second-hop query
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the first critical missing piece of evidence and generate a search query for it.",
                "stage_action": (
                    "Based on the retrieved passages, determine the most critical piece of evidence still missing to verify the claim. "
                    "Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing? Which entities or relationships are involved? "
                    "How can this be phrased as a short, precise query?"
                ),
                "example_reasoning": (
                    "Example: 'Who discovered penicillin?'\n"
                    "Example: 'When was the Berlin Wall constructed?'")
                ,
                "dependencies": [1],
            },
            # Step 3: Generate second second-hop query (avoids duplication)
            {
                "number": 3,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a second, distinct missing piece of evidence (different from the first query) and generate a search query for it.",
                "stage_action": (
                    "Based on the retrieved passages and the first query generated, determine another critical piece of evidence still missing "
                    "(and not covered by the first query). Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence is still missing that is different from the first query's focus? "
                    "Which new entities or relationships are involved? How can this be phrased as a short, precise query?"
                ),
                "example_reasoning": (
                    "Example: 'What is the chemical formula of water?'\n"
                    "Example: 'Who wrote the novel 1984?'")
                ,
                "dependencies": [1, 2],
            },
            # Step 4: Second-hop retrieval branch 1
            {
                "number": 4,
                "title": "Retrieve with first second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},  # Step2 output (index=1)
                },
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval branch 2
            {
                "number": 5,
                "title": "Retrieve with second second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},  # Step3 output (index=2)
                },
                "dependencies": [3],
            },
            # Step 6: Synthesize evidence and generate third-hop query
            {
                "number": 6,
                "title": "Combine evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Combine all evidence gathered and identify the final missing piece, then generate a search query for it.",
                "stage_action": (
                    "Review the initial claim and all retrieved passages (from first hop and both second-hop branches). "
                    "Identify what critical evidence is still missing to fully verify the claim. "
                    "Write a concise search query to find this final piece of evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence has been found so far? What is still missing? "
                    "How can the missing piece be phrased as a short, precise query?"
                ),
                "example_reasoning": (
                    "Example: 'What was the cause of World War I?'\n"
                    "Example: 'How does photosynthesis work?'")
                ,
                "dependencies": [1, 4, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},  # Step6 output (index=5)
                },
                "dependencies": [6],
            },
        ],
    }