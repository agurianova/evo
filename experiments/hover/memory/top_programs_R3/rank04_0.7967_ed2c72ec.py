def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to maximize retrieval of gold-standard evidence by generating precise search queries at each step. Focus exclusively on identifying missing information and crafting queries that will retrieve specific gold documents. When instructed to provide a query, output ONLY the search terms with no additional text, explanations, or formatting.",
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
            # Step 2: Generate second-hop query (initial gap focus)
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information after the first hop and generate a precise search query.",
                "stage_action": (
                    "Based on the first-hop passages, determine what specific evidence is still missing to verify the claim. "
                    "Write a concise search query to find this evidence. Prioritize the single most critical missing piece. "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact or entity in the claim lacks supporting evidence from the first-hop passages?\n"
                    "Which missing piece would most directly confirm or refute the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "First-hop passages: [1] Eiffel Tower | ... built in Paris ... [2] ... Gustave Eiffel ... Paris ...\n"
                    "Missing: Original intended location.\n"
                    "Query: 'Eiffel Tower original intended location'"
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
            # Step 4: Generate third-hop query (residual gap focus with multi-term)
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify residual gaps after two hops and generate a dual-term query to cover top possibilities.",
                "stage_action": (
                    "Review all evidence from first and second hops. Determine the top two missing evidence pieces. "
                    "Generate a search query using OR to cover both possibilities (e.g., 'A OR B'). "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific evidence remains missing after reviewing both hop results?\n"
                    "Which two plausible explanations or facts would most likely fill this gap?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "Evidence: First hop: built in Paris. Second hop: 'proposed for Barcelona but rejected.'\n"
                    "Missing: Confirmation of Barcelona proposal and rejection reason.\n"
                    "Query: 'Eiffel Tower Barcelona proposal reason OR rejection cause'"
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
            # Step 6: Generate fourth-hop query (comprehensive gap focus)
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final missing evidence and generate a comprehensive multi-term query.",
                "stage_action": (
                    "After reviewing all evidence from three hops, determine the critical missing evidence. "
                    "Generate a search query using OR to cover all top plausible descriptions (e.g., 'A OR B OR C'). "
                    "Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the single most critical evidence still missing?\n"
                    "What are the top three ways this missing evidence might be described in sources?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
                    "Evidence: First hop: Paris location. Second hop: Barcelona proposal. Third hop: 'rejected due to cost concerns'.\n"
                    "Missing: Official documentation of rejection reason.\n"
                    "Query: 'Eiffel Tower Barcelona rejection reason cost OR budget OR financial'"
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