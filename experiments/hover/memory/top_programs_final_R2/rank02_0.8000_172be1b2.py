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
            # Step 2: Generate primary second-hop query (with fallback)
            {
                "number": 2,
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information from first-hop evidence and generate precise search query, with fallback for empty evidence",
                "stage_action": (
                    "If the first-hop retrieval (step1) returned no passages, generate a broader query for the main entity of the claim (e.g., the subject). "
                    "Otherwise, analyze the retrieved passages to determine the most critical missing fact needed to verify the claim. "
                    "Identify the key entity involved in the missing fact, then formulate a query that targets the unverified fact about that entity. "
                    "Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "What if there is no first-hop evidence? How should you adjust your query? "
                    "Which key entity in the claim lacks supporting evidence? "
                    "What precise fact is still missing about this entity? "
                    "How can we formulate a query using domain-specific terminology to find this fact?"
                ),
                "example_reasoning": (
                    "Case 1 (evidence exists):\n"
                    "Claim: 'Photosynthesis converts light energy into chemical energy.'\n"
                    "Evidence: [1] Photosynthesis | The process used by plants to convert sunlight into energy.\n"
                    "Reasoning: The evidence describes conversion of sunlight (light energy) but does not specify the chemical form. "
                    "The key entity is 'photosynthesis' and the missing fact is the chemical storage molecule (ATP). "
                    "Query: 'photosynthesis chemical energy storage molecule'\n\n"
                    "Case 2 (no evidence):\n"
                    "Claim: 'The mitochondria are the powerhouse of the cell.'\n"
                    "Evidence: (none)\n"
                    "Reasoning: No evidence was retrieved. The main entity is 'mitochondria', so we generate a broad query for it. "
                    "Query: 'mitochondria'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate alternative second-hop query (true diversity)
            {
                "number": 3,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify a truly distinct missing information path and generate a diverse search query",
                "stage_action": (
                    "Analyze the first-hop evidence and the claim to identify a different unverified aspect of the claim that provides an alternative path to verify the claim. "
                    "Identify the key entity involved in this alternative aspect, then formulate a query that targets the unverified fact about that entity. "
                    "The alternative path must target a distinct topic from the primary query (step2). "
                    "Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "What is a different unverified aspect of the claim that is distinct from the primary query (step2)? "
                    "How does this aspect provide an alternative path to verify the claim? "
                    "How can you formulate a query that targets only this alternative aspect without overlapping with the primary query's topic?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919.'\n"
                    "Evidence: [1] Treaty of Versailles | Ended World War I, signed in Paris on June 28, 1919.\n"
                    "Reasoning: The evidence confirms the signing year (1919) but does not mention the location. "
                    "The key entity is 'Treaty of Versailles' and the alternative missing fact is the signing location (Paris). "
                    "Query: 'Treaty of Versailles signing location'"
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
            # Step 6: Generate third-hop query with internal summarization
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gaps from summarized evidence and generate precise query",
                "stage_action": (
                    "First, concisely summarize the verified facts and remaining gaps from all retrieved evidence (first-hop, primary second-hop, and alternative second-hop). "
                    "Then, identify the key entity involved in the most critical unverified component of the claim, and formulate a query that targets the missing fact about that entity. "
                    "Output ONLY the search query string."
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
                    "Summary: The evidence confirms mitochondria produce ATP and are called the powerhouse, but does not explain the mechanism.\n"
                    "Unverified component: The specific mechanism of ATP production (e.g., oxidative phosphorylation). Key entity: 'mitochondria'.\n"
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