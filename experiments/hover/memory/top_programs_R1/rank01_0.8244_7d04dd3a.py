def entrypoint():
    return {
        "system_prompt": "You verify claims through multi-hop evidence gathering, identifying missing links between facts. When generating search queries, prioritize short, entity-focused queries with minimal terms to maximize BM25 effectiveness.",
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
            # Step 2: Multi-hop gap anticipation and first query generation
            {
                "number": 2,
                "title": "Break down gaps and generate first query",
                "step_type": "llm",
                "aim": "Extract key facts and break down verification gaps into intermediate evidence needs with explicit entity types.",
                "stage_action": (
                    "List confirmed facts from retrieved passages. For missing information, specify intermediate evidence required to bridge to the final claim, with entity types (e.g., host_country for World Cup). Generate ONLY a minimal search query for the next hop."
                ),
                "reasoning_questions": (
                    "What facts are confirmed? What is the immediate next piece of evidence needed? What entity type does it represent?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'City of 1952 Olympics hosted 1998 World Cup'. Known: 1952 Olympics in Helsinki. Missing: Host country of 1998 World Cup (entity: country). Query: '1998 FIFA World Cup host country'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Multi-hop gap re-identification and second query generation
            {
                "number": 4,
                "title": "Re-identify gaps and generate second query",
                "step_type": "llm",
                "aim": "Re-identify gaps from combined evidence (first and second hops), breaking down complex gaps, and generate minimal query for third hop.",
                "stage_action": (
                    "Integrate facts from all retrieved passages. Identify remaining gaps, including emergent ones from new evidence, and break into intermediate steps with entity types. Generate ONLY a minimal search query for the next hop."
                ),
                "reasoning_questions": (
                    "What new facts were added by second-hop evidence? Which initial gaps are resolved? What new gaps emerge? What is the immediate next evidence needed?"
                ),
                "example_reasoning": (
                    "Example: Step1: Helsinki for 1952 Olympics. Step3: France hosted 1998 World Cup. Known: Helsinki, France. Missing: Capital of France (entity: city) to match 'city' in claim. Query: 'France capital city'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Comprehensive gap synthesis and third query generation
            {
                "number": 6,
                "title": "Re-identify gaps and generate third query",
                "step_type": "llm",
                "aim": "Re-identify gaps from all evidence, breaking down complex gaps, and generate minimal query for fourth hop.",
                "stage_action": (
                    "Synthesize all retrieved passages. Identify remaining gaps, break into intermediate steps with entity types. If no gaps remain, output empty string. Otherwise, generate ONLY a minimal search query for the next hop."
                ),
                "reasoning_questions": (
                    "What is the current state of verification? What minimal evidence is still missing? How would domain experts phrase a query for the immediate next step?"
                ),
                "example_reasoning": (
                    "Example: Step1: Helsinki, Step3: France, Step5: Paris. Known: Helsinki, France, Paris. Claim verified? Yes. Output: ''"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }