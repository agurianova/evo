def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Your task is to generate search queries and summarize evidence to maximize retrieval of relevant passages. Be precise: when asked for a search query, output ONLY the query string with no additional text. When summarizing evidence, focus on facts directly relevant to verifying the claim. For ambiguous claims, consider all plausible interpretations and formulate a query that captures the most critical aspects for verification.",
        "steps": [
            # Step 1: Generate first-hop query
            {
                "number": 1,
                "title": "Generate first-hop query",
                "step_type": "llm",
                "aim": "Generate an effective first-hop search query from the claim.",
                "stage_action": "Reformulate the claim into a concise, effective search query that will retrieve relevant Wikipedia passages. Provide ONLY the search query string, no additional text.",
                "reasoning_questions": "What are the main entities and the core fact in the claim? How can we phrase a concise search query to retrieve the most direct evidence for the claim?",
                "example_reasoning": "Example: 'Albert Einstein birth date and place'",
                "dependencies": [],
            },
            # Step 2: First-hop retrieval (k=7 for precision)
            {
                "number": 2,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate a second-hop search query based on first-hop passages.",
                "stage_action": "Read the first-hop retrieved passages and identify missing information needed to verify the claim. Generate a concise search query to find that information. Provide ONLY the search query string, no additional text.",
                "reasoning_questions": "Given the first-hop passages, what specific fact is missing to verify the claim? How can we phrase a concise search query to find that missing fact?",
                "example_reasoning": "Example: If the first hop provided birth date but not place, then 'Albert Einstein birth place'",
                "dependencies": [2],
            },
            # Step 4: Second-hop deep retrieval
            {
                "number": 4,
                "title": "Retrieve second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Generate third-hop query
            {
                "number": 5,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a third-hop search query based on all retrieved evidence so far.",
                "stage_action": "Read the first-hop and second-hop retrieved passages. Identify any remaining gaps in the evidence. Generate a concise search query to find the missing information. Provide ONLY the search query string, no additional text.",
                "reasoning_questions": "Considering both first-hop and second-hop passages, what critical piece of evidence is still missing? Focus on relationships between entities or contextual facts that are essential for verification.",
                "example_reasoning": "Example: 'Einstein Nobel Prize year'",
                "dependencies": [2, 4],
            },
            # Step 6: Third-hop deep retrieval
            {
                "number": 6,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [5],
            },
            # Step 7: Generate fourth-hop query
            {
                "number": 7,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a fourth-hop search query based on all retrieved evidence so far.",
                "stage_action": "Read the first-hop, second-hop, and third-hop retrieved passages. Identify any remaining gaps in the evidence. Generate a concise search query to find the missing information. Provide ONLY the search query string, no additional text.",
                "reasoning_questions": "With the evidence from three hops, what subtle inconsistency or additional context is needed? What is the most critical remaining gap in the evidence?",
                "example_reasoning": "Example: 'Einstein theory of relativity publication date'",
                "dependencies": [2, 4, 6],
            },
            # Step 8: Fourth-hop deep retrieval
            {
                "number": 8,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Generate fifth-hop query (final gap check)
            {
                "number": 9,
                "title": "Generate final gap query",
                "step_type": "llm",
                "aim": "Perform final gap analysis and generate a query for any remaining missing evidence.",
                "stage_action": "Analyze all retrieved passages (from first to fourth hop) and the original claim. Identify if there are any gaps in the evidence that prevent verification. If gaps exist, generate a concise search query to find the missing information. Provide ONLY the search query string, no additional text.",
                "reasoning_questions": "After reviewing all evidence from four hops, what single fact would definitively verify or refute the claim?",
                "example_reasoning": "Example: 'Einstein immigration to USA date'",
                "dependencies": [2, 4, 6, 8],
            },
            # Step 10: Fifth-hop deep retrieval
            {
                "number": 10,
                "title": "Retrieve fifth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }
