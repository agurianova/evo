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
                    "Claim: 'Photosynthesis converts light energy into chemical energy.'\n"
                    "Evidence: [1] Photosynthesis | The process used by plants to convert sunlight into energy.\n"
                    "Missing: the chemical form of the energy. Query: 'photosynthesis chemical energy storage molecule'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate alternative second-hop query (robust to primary query redundancy)
            {
                "number": 3,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify an alternative missing information path and generate a distinct search query",
                "stage_action": (
                    "Analyze the first-hop evidence and the claim to identify an alternative missing fact that provides a different path to verify the claim. "
                    "If the primary query (from step 2) appears to seek information already present in the evidence, generate a query for a different missing fact. "
                    "Otherwise, generate a query that avoids the topic of the primary query. "
                    "Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "1. Does the primary query (step2) target a fact that is already supported by the first-hop evidence? "
                    "2. If yes, what other aspect of the claim is still missing? If no, what is a different unverified aspect of the claim? "
                    "3. How does this query differ from the primary path in step 2? "
                    "4. Can you rephrase to target distinct evidence sources?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919.'\n"
                    "Evidence: [1] Treaty of Versailles | Ended World War I, signed in Paris on June 28, 1919.\n"
                    "Primary query (step2): 'Treaty of Versailles signing year'  [Note: year is already in evidence]\n"
                    "Alternative missing: signing location (Paris). Query: 'Treaty of Versailles signing location'"
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
            # Step 6: Generate third-hop query with verified-facts summary
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gaps from all evidence and generate precise query",
                "stage_action": (
                    "Review all retrieved evidence (first-hop, primary second-hop, and alternative second-hop) to summarize verified facts. "
                    "Then, identify the most critical unverified component of the claim. "
                    "Output ONLY the search query string for the most critical missing fact."
                ),
                "reasoning_questions": (
                    "1. What specific parts of the claim have been verified by the evidence? "
                    "2. What specific part of the claim remains unverified? "
                    "3. Could there be multiple unverified components? Which one is most critical to verify the claim? "
                    "4. How can we formulate a query that targets only the unverified part without overlapping with existing evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The mitochondria are the powerhouse of the cell.'\n"
                    "Evidence:\n"
                    "  [1] Mitochondrion | Organelle known as the powerhouse of the cell, producing ATP.\n"
                    "  [2] Cellular respiration | Process that occurs in mitochondria to produce ATP.\n"
                    "  [3] ATP | Energy currency of the cell produced by mitochondria.\n"
                    "Verified: Mitochondria produce ATP and are called the powerhouse.\n"
                    "Unverified: The specific mechanism of ATP production (e.g., oxidative phosphorylation).\n"
                    "Query: 'mitochondria ATP production mechanism'"
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