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
                    "Claim: 'Photosynthesis converts carbon dioxide and water into glucose and oxygen.'\n"
                    "Evidence: [1] Photosynthesis | The process used by plants to convert light energy into chemical energy.\n"
                    "Missing: chemical equation. Query: 'photosynthesis chemical equation'"
                ),
                "dependencies": [1],
            },
            # Step 3: Primary second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve primary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate secondary second-hop query (distinct from primary)
            {
                "number": 4,
                "title": "Generate secondary second-hop query",
                "step_type": "llm",
                "aim": "Identify a distinct critical evidence gap (not addressed by primary second-hop) and generate precise query",
                "stage_action": (
                    "Analyze first-hop and primary second-hop evidence to find a critical missing fact DIFFERENT from what the primary query targeted. "
                    "Focus on unverified entities/facts untouched by prior evidence. Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "Which claim component remains unverified AND was NOT addressed by the primary second-hop query? "
                    "What minimal precise fact would verify this distinct gap? "
                    "How to phrase this using domain terminology to avoid overlap with prior queries?"
                ),
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Treaty of Versailles was signed in Paris in 1919.'\n"
                    "Evidence from first-hop:\n[1] Treaty of Versailles | ... signed at the end of World War I ...\n"
                    "Evidence from primary second-hop (query: 'Treaty of Versailles signing year'):\n[1] Signing of Treaty of Versailles | ... signed on June 28, 1919 ...\n"
                    "Residual gaps: location (Paris) not mentioned. Query: 'Treaty of Versailles signing location'\n\n"
                    "Example 2:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in different sciences.'\n"
                    "Evidence from first-hop:\n[1] Marie Curie | ... physicist and chemist ...\n"
                    "Evidence from primary second-hop (query: 'Marie Curie Nobel Prizes years'):\n[1] Nobel Prize in Physics | ... awarded to Marie Curie in 1903 ...\n[2] Nobel Prize in Chemistry | ... awarded to Marie Curie in 1911 ...\n"
                    "Residual gaps: confirmation that physics and chemistry are distinct sciences in Nobel context. Query: 'Nobel Prize categories distinct sciences'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Secondary second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve secondary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query from combined evidence
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the single most critical residual evidence gap from ALL evidence and generate precise query",
                "stage_action": (
                    "Synthesize evidence from first-hop, primary and secondary second-hops to list verified/unverified claim components. "
                    "Target ONLY the top unverified component with minimal precise query. Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "1. Which claim components are FULLY verified by current evidence?\n"
                    "2. Which components remain UNVERIFIED or PARTIALLY verified?\n"
                    "3. For the #1 unverified component, what MINIMAL fact would verify it?\n"
                    "4. Which entity should the query target to find this fact MOST PRECISELY?"
                ),
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in different sciences.'\n"
                    "Evidence from first-hop:\n[1] Marie Curie | ... physicist and chemist ...\n"
                    "Evidence from primary second-hop:\n[1] Nobel Prize in Physics | ... awarded to Marie Curie in 1903 ...\n[2] Nobel Prize in Chemistry | ... awarded to Marie Curie in 1911 ...\n"
                    "Evidence from secondary second-hop:\n[1] Nobel Prize categories | ... six categories: Physics, Chemistry, Medicine, Literature, Peace, and Economics ...\n"
                    "Residual gaps: confirmation that Physics and Chemistry are distinct categories. Query: 'Nobel Prize Physics and Chemistry distinct categories'\n\n"
                    "Example 2:\n"
                    "Claim: 'The Treaty of Versailles was signed in Paris in 1919.'\n"
                    "Evidence from first-hop:\n[1] Treaty of Versailles | ... signed at the end of World War I ...\n"
                    "Evidence from primary second-hop:\n[1] Signing of Treaty of Versailles | ... signed on June 28, 1919 ...\n"
                    "Evidence from secondary second-hop:\n[1] Paris | ... capital of France ...\n[2] Versailles | ... a city in France, location of the Palace of Versailles ...\n"
                    "Residual gaps: signing occurred in Paris (not Versailles city). Query: 'Treaty of Versailles signing location Paris'"
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
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }