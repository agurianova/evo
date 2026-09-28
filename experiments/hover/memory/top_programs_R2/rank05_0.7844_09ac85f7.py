def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checking assistant. Your task is to verify claims by retrieving relevant evidence from Wikipedia abstracts. Be thorough: identify key entities and missing facts precisely. For query generation steps, output ONLY the search query string with no additional text.",
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the critical missing information from first-hop evidence and generate a precise search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine the most critical missing fact needed to verify the claim. "
                    "Focus on key entities and unverified facts. "
                    "WARNING: Output ONLY the search query string with no additional text. Any extra text causes system failure."
                ),
                "reasoning_questions": (
                    "Which key entity in the claim lacks supporting evidence? "
                    "What precise fact is still missing? "
                    "How can we formulate a query using domain-specific terminology to find this fact?"
                ),
                "example_reasoning": (
                    "Claim: [claim]\n"
                    "Evidence:\n[1] [Title] | [sentence1] [sentence2] ...\n"
                    "Missing: [unverified fact]. Query: [query string]"
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
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify critical missing information from combined first and second-hop evidence and generate precise query",
                "stage_action": (
                    "Analyze ALL retrieved passages to determine the exact missing evidence needed for verification. "
                    "Focus exclusively on unverified facts and residual gaps. "
                    "WARNING: Output ONLY the search query string with no additional text. Any extra text causes system failure."
                ),
                "reasoning_questions": (
                    "What specific fact remains unverified after reviewing all evidence? "
                    "Which entity should the query target to resolve the claim? "
                    "How can we avoid terms already covered by previous evidence?"
                ),
                "example_reasoning": (
                    "Claim: [claim]\n"
                    "Evidence:\n[retrieved passages]\n"
                    "Missing: [unverified fact]. Query: [query string]"
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
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gaps from all prior results and generate precise query",
                "stage_action": (
                    "Analyze ALL evidence from previous hops to determine the exact missing verification fact. "
                    "Focus exclusively on unverified elements and residual gaps. "
                    "WARNING: Output ONLY the search query string with no additional text. Any extra text causes system failure."
                ),
                "reasoning_questions": (
                    "What specific fact remains unverified after reviewing all evidence? "
                    "Which entity should the query target to resolve the claim? "
                    "How can we avoid terms already covered by previous evidence?"
                ),
                "example_reasoning": (
                    "Claim: [claim]\n"
                    "Evidence:\n[retrieved passages]\n"
                    "Missing: [unverified fact]. Query: [query string]"
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