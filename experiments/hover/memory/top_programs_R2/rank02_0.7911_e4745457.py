def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert. Retrieve all evidence needed to verify the claim.",
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
            # Step 2: Generate first second-hop query (entity-focused)
            {
                "number": 2,
                "title": "Generate entity-focused query",
                "step_type": "llm",
                "aim": "Identify main entities in claim and generate search query about one key entity.",
                "stage_action": (
                    "Based on the retrieved passages, determine a key entity (e.g., person, organization) central to the claim. "
                    "Use key terms from the passages to form a detailed search query about this entity. "
                    "Output the query in the format: 'QUERY: [your query]'"
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example 1 (Scientific): For claim 'Marie Curie won two Nobel Prizes', output: 'QUERY: Marie Curie (physicist) Nobel Prize achievements 1903'",
                    "Example 2 (Historical): For claim 'The Treaty of Versailles ended WWI', output: 'QUERY: Treaty of Versailles (1919) World War I conclusion terms'",
                    "Example 3 (Health): For claim 'mRNA vaccines were first used in 2020', output: 'QUERY: mRNA vaccine (Pfizer-BioNTech) emergency authorization 2020'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second second-hop query (event-focused)
            {
                "number": 3,
                "title": "Generate event-focused query",
                "step_type": "llm",
                "aim": "Identify key event/relationship in claim and generate search query about it.",
                "stage_action": (
                    "Based on the retrieved passages, determine a key event or relationship central to the claim. "
                    "Use key terms from the passages to form a detailed search query about this. "
                    "Output the query in the format: 'QUERY: [your query]'"
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example 1 (Scientific): For claim 'Marie Curie won two Nobel Prizes', output: 'QUERY: Nobel Prize in Physics 1903 (shared with Pierre Curie)'",
                    "Example 2 (Historical): For claim 'The Treaty of Versailles ended WWI', output: 'QUERY: World War I armistice date signing location'",
                    "Example 3 (Health): For claim 'mRNA vaccines were first used in 2020', output: 'QUERY: COVID-19 vaccine development timeline FDA approval'",
                ),
                "dependencies": [1],
            },
            # Step 4: Second-hop retrieval (entity)
            {
                "number": 4,
                "title": "Retrieve entity-focused passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval (event)
            {
                "number": 5,
                "title": "Retrieve event-focused passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Synthesize evidence and generate third-hop query
            {
                "number": 6,
                "title": "Generate final verification query",
                "step_type": "llm",
                "aim": "Integrate all evidence and identify final missing piece for verification.",
                "stage_action": (
                    "Review the claim and all retrieved passages (steps 1, 4, 5). Determine what critical evidence is still missing "
                    "to fully verify the claim. Output the query in the format: 'QUERY: [your query]'"
                ),
                "reasoning_questions": (
                    "What key entities/events are already covered?\n"
                    "List specific unverified facts (1-2 critical items).\n"
                    "Which unverified fact is most essential for verification?\n"
                    "What search terms would best capture this missing evidence?"
                ),
                "example_reasoning": (
                    "Example 1 (Scientific): If missing second Nobel Prize info, output: 'QUERY: Marie Curie second Nobel Prize Chemistry 1911'",
                    "Example 2 (Historical): If missing treaty ratification date, output: 'QUERY: Treaty of Versailles ratification date US Senate'",
                    "Example 3 (Health): If missing vaccine efficacy data, output: 'QUERY: Pfizer-BioNTech vaccine efficacy clinical trial results'",
                ),
                "dependencies": [1, 4, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve final verification passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }