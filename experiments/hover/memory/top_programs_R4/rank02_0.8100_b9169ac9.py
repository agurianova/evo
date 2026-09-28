def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Your task is to verify claims by retrieving relevant Wikipedia passages through multi-hop reasoning. After each retrieval, summarize key facts directly relevant to the claim and identify evidence gaps. When generating search queries:\n  - Use multiple specific terms to target missing information (e.g., 'entity relationship fact')\n  - Prioritize concrete entities, dates, and relationships over vague concepts\n  - Structure queries as minimal complete phrases for precision\nFor third-hop queries, focus on the most critical remaining gap after two hops of evidence.\nAlways generate a search query when requested; do not output 'NO_MORE_HOPS'. Prioritize factual accuracy and relevance to the claim.",
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
            # Step 2: Generate primary second-hop query
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the primary evidence gap from first-hop passages and generate a precise query",
                "stage_action": (
                    "Based on the first-hop passages, determine the most critical missing fact to verify the claim. "
                    "Write a concise search query targeting ONLY this missing information. "
                    "Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "What concrete fact is most needed to verify the claim? "
                    "Which entities/relationships require clarification? "
                    "How can the query avoid ambiguity using specific terms?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages: 'Marie Curie won Nobel Prizes in Physics (1903) and Chemistry (1911).'",
                    "Missing: Whether any woman won before 1903. ",
                    "Query: 'first woman Nobel Prize winner before 1903'"
                ),
                "dependencies": [1],
            },
            # Step 3: First second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate secondary second-hop query
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a distinct secondary evidence gap from all available passages and generate a precise query",
                "stage_action": (
                    "Based on the first-hop and first second-hop passages, determine another critical missing fact "
                    "that is distinct from the first gap. Write a concise search query targeting ONLY this "
                    "missing information. Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "What additional fact is needed beyond the first gap? "
                    "Which entities/relationships remain unclear? "
                    "How can the query target a different angle of evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie was the first woman to win a Nobel Prize.'\n"
                    "Hop1: 'Marie Curie won Nobel Prizes in Physics (1903) and Chemistry (1911).'\n"
                    "Hop2: 'Women Nobel laureates before 1903: none in Physics or Chemistry.'\n"
                    "Missing: Clarification that the 1903 Physics Prize was shared but she was a woman winner.\n"
                    "Query: 'Marie Curie 1903 Nobel Prize co-winners'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Second second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve second second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical remaining evidence gap from all passages and generate a precise query",
                "stage_action": (
                    "Based on the first-hop, first second-hop, and second second-hop passages, "
                    "determine the most critical missing fact that remains unaddressed. "
                    "Write a concise search query targeting ONLY this missing information. "
                    "Provide ONLY the search query string, no additional text."
                ),
                "reasoning_questions": (
                    "What concrete fact is still missing after two hops? "
                    "Which entities/relationships remain unresolved? "
                    "How can the query use specific terms to target the gap?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie was the first woman to win a Nobel Prize.'\n"
                    "Hop1: 'Marie Curie won Nobel Prizes in Physics (1903) and Chemistry (1911).'\n"
                    "Hop2a: 'Women Nobel laureates before 1903: none in Physics or Chemistry.'\n"
                    "Hop2b: 'Marie Curie 1903 Nobel Prize co-winners: Pierre Curie and Henri Becquerel.'\n"
                    "Missing: Whether Marie Curie was recognized as a woman winner in 1903 despite sharing.\n"
                    "Query: 'Marie Curie 1903 Nobel Prize woman winner status'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval
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