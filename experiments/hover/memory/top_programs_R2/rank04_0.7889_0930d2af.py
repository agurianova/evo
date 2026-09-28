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
            # Step 2: Generate primary second-hop query
            {
                "number": 2,
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify the primary missing information from first-hop evidence and generate a precise search query",
                "stage_action": (
                    "Analyze the retrieved passages to determine the most critical missing fact needed to verify the claim. "
                    "Focus on key entities and unverified facts. Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "Which key entity in the claim lacks supporting evidence? "
                    "What precise fact is still missing? "
                    "How can we formulate a query using domain-specific terminology to find this fact?"
                ),
                "example_reasoning": (
                    "Example 1 (History):\n"
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Evidence: [1] Eiffel Tower | ... built for the 1889 World's Fair ...\n"
                    "Missing: intended duration. Query: 'Eiffel Tower original permit duration'\n\n"
                    "Example 2 (Science):\n"
                    "Claim: 'Vitamin C prevents scurvy by aiding collagen synthesis.'\n"
                    "Evidence: [1] Scurvy | ... disease caused by vitamin C deficiency ...\n"
                    "Missing: mechanism of collagen synthesis. Query: 'Vitamin C collagen hydroxylation mechanism'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate alternative second-hop query (with primary query context)
            {
                "number": 3,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify an alternative missing information path using primary query context and generate a distinct search query",
                "stage_action": (
                    "Analyze the retrieved passages and the primary query (output of previous step) to identify an alternative missing fact. "
                    "Generate a query that avoids semantic overlap with the primary query while providing a different verification path. "
                    "Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "What is a different unverified aspect of the claim? "
                    "Which entity or relationship might have an alternative explanation? "
                    "How does this query differ semantically from the primary query? "
                    "Can you rephrase the claim from an opposite perspective to find alternative evidence?"
                ),
                "example_reasoning": (
                    "Example 1 (History):\n"
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Evidence: [1] Eiffel Tower | ... built for the 1889 World's Fair ...\n"
                    "Primary query: 'Eiffel Tower original permit duration'\n"
                    "Alternative missing: whether dismantling occurred as planned. Query: 'Eiffel Tower dismantled after World's Fair'\n\n"
                    "Example 2 (Science):\n"
                    "Claim: 'Vitamin C prevents scurvy by aiding collagen synthesis.'\n"
                    "Evidence: [1] Scurvy | ... disease caused by vitamin C deficiency ...\n"
                    "Primary query: 'Vitamin C collagen hydroxylation mechanism'\n"
                    "Alternative missing: historical evidence of scurvy prevention. Query: 'British Navy lemon juice scurvy 1747'"
                ),
                "dependencies": [1, 2],
            },
            # Step 4: Primary second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve primary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 5: Alternative second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve alternative second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Generate third-hop query from combined evidence
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gaps from combined second-hop results and generate precise query",
                "stage_action": (
                    "Analyze ALL passages from primary and alternative second-hop retrievals to determine the exact missing evidence. "
                    "Focus exclusively on unverified facts and residual gaps. Do not re-analyze facts that are already verified in the first-hop or second-hop evidence. "
                    "Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "List each unverified component of the claim explicitly. "
                    "For each unverified component, what is the most precise fact needed? "
                    "Which entity should the query target to resolve the residual gap? "
                    "How can we avoid terms already covered by previous evidence?"
                ),
                "example_reasoning": (
                    "Example 1 (History):\n"
                    "Claim: 'The Eiffel Tower was originally intended to be a temporary structure.'\n"
                    "Evidence:\n[1] Eiffel Tower | ... built for the 1889 World's Fair ...\n"
                    "[2] Eiffel Tower | ... permit granted for 20 years ...\n"
                    "[3] Eiffel Tower | ... dismantling planned after fair ...\n"
                    "Residual gap: actual dismantling decision. Query: 'Eiffel Tower dismantling decision 1909'\n\n"
                    "Example 2 (Science):\n"
                    "Claim: 'Vitamin C prevents scurvy by aiding collagen synthesis.'\n"
                    "Evidence:\n[1] Scurvy | ... disease caused by vitamin C deficiency ...\n"
                    "[2] Collagen | ... requires hydroxylation of proline residues ...\n"
                    "[3] Vitamin C | ... cofactor for prolyl hydroxylase enzyme ...\n"
                    "Residual gap: clinical proof of scurvy prevention. Query: 'James Lind scurvy controlled trial'"
                ),
                "dependencies": [1, 4, 5],
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