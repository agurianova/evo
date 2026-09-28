def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Your task is to retrieve ALL passages necessary to verify the claim through multi-hop retrieval. Stop as soon as ALL evidence is found to preserve hops for complex claims. At each step, analyze current evidence to identify precise missing information, then generate ONLY the search query needed to find it.",
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
                "title": "Generate second-hop query or stop",
                "step_type": "llm",
                "aim": "Determine if first-hop evidence is sufficient OR generate precise second-hop query",
                "stage_action": (
                    "Analyze the first-hop passages to verify the claim. If ALL claim components are verified, output 'SUFFICIENT'. "
                    "Otherwise, generate a precise search query for missing evidence. "
                    "Output ONLY the query or 'SUFFICIENT', no additional text."
                ),
                "reasoning_questions": (
                    "1. Which specific claim elements remain unverified by the first-hop evidence?\n"
                    "2. What is the most direct entity/event to target for missing evidence?\n"
                    "3. How can we phrase a query that isolates this missing piece without overlap?\n"
                    "4. If sufficient, which claim components were verified?"
                ),
                "example_reasoning": (
                    "Example 1 (Sufficient):\n"
                    "Claim: 'Mount Everest is the highest mountain above sea level'\n"
                    "- Passages confirm height ranking and sea level measurement\n"
                    "- ALL elements verified → Output: 'SUFFICIENT'\n\n"
                    
                    "Example 2 (Query):\n"
                    "Claim: 'The Treaty of Versailles was signed in 1919'\n"
                    "- Passages confirm signing year but not location\n"
                    "- Missing: where signing occurred\n"
                    "- Entities: Treaty of Versailles, 1919\n"
                    "- Query: 'location signing Treaty of Versailles 1919'\n\n"
                    
                    "Example 3 (Negation Edge Case):\n"
                    "Claim: 'The Earth is not flat'\n"
                    "- Passages confirm spherical Earth but not flat-Earth refutation\n"
                    "- Missing: evidence specifically debunking flat Earth\n"
                    "- Entities: Earth shape, flat Earth myth\n"
                    "- Query: 'scientific evidence against flat Earth theory'\n\n"
                    
                    "Example 4 (Multi-Entity):\n"
                    "Claim: 'Einstein and Newton both contributed to physics'\n"
                    "- Passages confirm Einstein's relativity but not Newton's laws\n"
                    "- Missing: Newton's foundational physics work\n"
                    "- Entities: Isaac Newton, classical mechanics\n"
                    "- Query: 'Isaac Newton contributions physics Principia'\n\n"
                    
                    "Example 5 (Error Case):\n"
                    "Claim: 'Water boils at 100°C'\n"
                    "- Passages confirm boiling point at standard pressure\n"
                    "- Missing: Celsius scale context\n"
                    "- INCORRECT: 'The boiling point of water is 100 degrees Celsius because...' (extra text)\n"
                    "- CORRECT: 'Celsius scale water boiling point'"
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
                "title": "Generate third-hop query or stop",
                "step_type": "llm",
                "aim": "Determine if combined evidence is sufficient OR generate precise third-hop query",
                "stage_action": (
                    "Analyze first-hop AND second-hop passages to verify the claim. If ALL claim components are verified, output 'SUFFICIENT'. "
                    "Otherwise, generate a precise search query for missing evidence. "
                    "Output ONLY the query or 'SUFFICIENT', no additional text."
                ),
                "reasoning_questions": (
                    "1. Which specific claim elements remain unverified by the combined evidence?\n"
                    "2. What UNIQUE entity can retrieve the missing information?\n"
                    "3. How to phrase the most targeted query avoiding previous terms?\n"
                    "4. If sufficient, list verified components with passage IDs"
                ),
                "example_reasoning": (
                    "Example 1 (Sufficient):\n"
                    "Claim: 'Vitamin C prevents scurvy'\n"
                    "- First hop: links scurvy to vitamin deficiency\n"
                    "- Second-hop: shows citrus prevents scurvy\n"
                    "- ALL elements verified → Output: 'SUFFICIENT'\n\n"
                    
                    "Example 2 (Query):\n"
                    "Claim: 'The Eiffel Tower was originally intended to be temporary'\n"
                    "- First hop: confirms temporary structure but not demolition reason\n"
                    "- Second-hop: shows 1909 demolition plan but not preservation reason\n"
                    "- Missing: why demolition was canceled\n"
                    "- Alternative entities: Gustave Eiffel, military use\n"
                    "- Query: 'military significance Eiffel Tower 1909'\n\n"
                    
                    "Example 3 (Negation Edge Case):\n"
                    "Claim: 'Photosynthesis does not require oxygen'\n"
                    "- First hop: confirms photosynthesis produces oxygen\n"
                    "- Second-hop: shows light-dependent reactions\n"
                    "- Missing: explicit statement about oxygen not being required\n"
                    "- Entities: photosynthesis, oxygen requirement\n"
                    "- Query: 'does photosynthesis require oxygen input'\n\n"
                    
                    "Example 4 (Error Case):\n"
                    "Claim: 'Marie Curie won two Nobel Prizes'\n"
                    "- First hop: confirms two prizes but not years\n"
                    "- Second-hop: shows 1903 Physics prize\n"
                    "- INCORRECT: 'SUFFICIENT because two prizes are confirmed' (missing Chemistry prize year)\n"
                    "- CORRECT: 'Marie Curie Nobel Chemistry prize year'"
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
                "title": "Generate fourth-hop query or stop",
                "step_type": "llm",
                "aim": "Determine if combined evidence is sufficient OR generate final query",
                "stage_action": (
                    "Analyze ALL retrieved passages (first-hop, second-hop, third-hop) to verify the claim. "
                    "If ALL claim components are verified, output 'SUFFICIENT'. "
                    "Otherwise, generate a precise search query for the missing evidence. "
                    "Output ONLY the query or 'SUFFICIENT', no additional text."
                ),
                "reasoning_questions": (
                    "1. Which specific claim elements remain unverified?\n"
                    "2. What is the most critical missing piece for verification?\n"
                    "3. How to phrase the most targeted query avoiding all previous terms?\n"
                    "4. If sufficient, list all verified components with passage IDs"
                ),
                "example_reasoning": (
                    "Example 1 (Sufficient):\n"
                    "Claim: 'Water boils at 100°C at sea level'\n"
                    "- First hop: confirms boiling point at standard pressure\n"
                    "- Second-hop: shows Celsius scale definition\n"
                    "- Third-hop: confirms sea level pressure standard\n"
                    "- ALL elements verified → Output: 'SUFFICIENT'\n\n"
                    
                    "Example 2 (Final Query):\n"
                    "Claim: 'Marie Curie won two Nobel Prizes'\n"
                    "- First hop: confirms two prizes but not years\n"
                    "- Second-hop: shows 1903 Physics prize details\n"
                    "- Third-hop: shows 1911 Chemistry prize nomination\n"
                    "- Missing: exact year of Chemistry prize\n"
                    "- Critical gap: 1911 prize year confirmation\n"
                    "- Query: 'Marie Curie Nobel Chemistry prize year 1911'\n\n"
                    
                    "Example 3 (Multi-Entity Edge Case):\n"
                    "Claim: 'Shakespeare and Dickens were both English writers'\n"
                    "- First hop: confirms Shakespeare's nationality\n"
                    "- Second-hop: confirms Dickens' works\n"
                    "- Third-hop: shows Dickens' birthplace\n"
                    "- Missing: explicit English nationality for Dickens\n"
                    "- Entities: Charles Dickens, English nationality\n"
                    "- Query: 'Charles Dickens country of birth nationality'\n\n"
                    
                    "Example 4 (Error Case):\n"
                    "Claim: 'The human genome has 3 billion base pairs'\n"
                    "- First hop: confirms base pair count\n"
                    "- Second-hop: shows sequencing project date\n"
                    "- Third-hop: describes assembly method\n"
                    "- INCORRECT: 'SUFFICIENT (all details covered)' (missing human specification)\n"
                    "- CORRECT: 'human genome project explicit organism specification'"
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