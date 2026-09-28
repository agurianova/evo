def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert. Retrieve all evidence needed to verify the claim.",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve initial evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate first second-hop query (Branch A)
            {
                "number": 2,
                "title": "Generate second-hop query A",
                "step_type": "llm",
                "aim": "Identify one critical missing fact from initial evidence and generate precise search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine ONE specific missing fact needed to verify the claim. "
                    "Write a concise search query that would retrieve this missing evidence. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What specific fact is currently missing to verify the claim? "
                    "Which entities or relationships in the claim are not yet supported by evidence?"
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages mention her Nobel wins but not gender precedence. "
                    "Query: 'Was Marie Curie the first woman to win a Nobel Prize?'")
            },
            # Step 3: Generate second second-hop query (Branch B)
            {
                "number": 3,
                "title": "Generate second-hop query B",
                "step_type": "llm",
                "aim": "Identify a different missing fact from initial evidence and generate alternative search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine A DIFFERENT specific missing fact needed to verify the claim. "
                    "Write a concise search query that would retrieve this alternative missing evidence. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What OTHER fact is missing that could support the claim? "
                    "Consider alternative perspectives or related entities that might provide evidence."
                ),
                "example_reasoning": (
                    "Example claim: 'Marie Curie was the first woman to win a Nobel Prize.' "
                    "Passages mention her Nobel wins but not other female laureates. "
                    "Query: 'List of female Nobel Prize winners before Marie Curie'")
            },
            # Step 4: Second-hop retrieval (Branch A)
            {
                "number": 4,
                "title": "Retrieve second-hop evidence A",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},  # Step 2 output
                },
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (Branch B)
            {
                "number": 5,
                "title": "Retrieve second-hop evidence B",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},  # Step 3 output
                },
                "dependencies": [3],
            },
            # Step 6: Combine evidence and generate third-hop query
            {
                "number": 6,
                "title": "Synthesize evidence and generate final query",
                "step_type": "llm",
                "aim": "Integrate all evidence to identify final missing piece and generate third-hop query",
                "stage_action": (
                    "Review all retrieved passages (initial and both second-hop) to determine what evidence is still missing. "
                    "Write a concise search query that would retrieve the final missing evidence needed for verification. "
                    "Output ONLY the search query without any additional text or explanations."
                ),
                "reasoning_questions": (
                    "What evidence has been found across all passages? "
                    "What specific gap remains that would confirm or refute the claim? "
                    "Which entities in this gap are most searchable?"
                ),
                "example_reasoning": (
                    "Example: Passages confirm Marie Curie won Nobel Prizes but don't address 'first woman'. "
                    "Query: 'Who was the first woman to win a Nobel Prize?'")
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve final evidence",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},  # Step 6 output
                },
                "dependencies": [6],
            },
        ],
    }