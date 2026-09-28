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
            # Step 2: Generate first alternative second-hop query
            {
                "number": 2,
                "title": "Generate first second-hop query or stop",
                "step_type": "llm",
                "aim": "Determine if first-hop evidence is sufficient OR generate query for first alternative second-hop path",
                "stage_action": (
                    "Analyze the first-hop passages to verify the claim. If ALL claim components are verified, output 'SUFFICIENT'. "
                    "Otherwise, generate a precise search query for the first alternative path to missing evidence. "
                    "Output ONLY the query or 'SUFFICIENT', no additional text."
                ),
                "reasoning_questions": (
                    "1. Which specific claim elements remain unverified by the first-hop evidence?\n"
                    "2. What is the most direct entity/event to target for the first evidence path?\n"
                    "3. How can we phrase a query that isolates this missing piece without overlap with first-hop?\n"
                    "4. If sufficient, which claim components were fully verified?"
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
                    
                    "Example 3 (Query):\n"
                    "Claim: 'Photosynthesis produces oxygen as a byproduct'\n"
                    "- Passages confirm oxygen production but not biochemical mechanism\n"
                    "- Missing: specific process step creating oxygen\n"
                    "- Entities: photosynthesis, oxygen byproduct\n"
                    "- Query: 'which step of photosynthesis releases oxygen'"
                ),
                "dependencies": [1],
            },
            # Step 3: First alternative second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second alternative second-hop query
            {
                "number": 4,
                "title": "Generate second second-hop query or stop",
                "step_type": "llm",
                "aim": "Determine if combined evidence (first-hop + first path) is sufficient OR generate query for second alternative path",
                "stage_action": (
                    "Analyze first-hop AND first second-hop passages to verify the claim. If ALL claim components are verified, output 'SUFFICIENT'. "
                    "Otherwise, generate a precise search query for the second alternative path to missing evidence. "
                    "Output ONLY the query or 'SUFFICIENT', no additional text."
                ),
                "reasoning_questions": (
                    "1. What NEW claim elements remain unverified after adding first second-hop evidence?\n"
                    "2. Which different entity/event (not used in first query) could bridge the gap?\n"
                    "3. How to phrase a query avoiding overlap with previous retrievals?\n"
                    "4. If sufficient, which new components were verified by second-hop?"
                ),
                "example_reasoning": (
                    "Example 1 (Sufficient):\n"
                    "Claim: 'Vitamin C prevents scurvy'\n"
                    "- First hop: links scurvy to vitamin deficiency\n"
                    "- First second-hop: shows citrus prevents scurvy\n"
                    "- ALL elements verified → Output: 'SUFFICIENT'\n\n"
                    
                    "Example 2 (Query):\n"
                    "Claim: 'The Eiffel Tower was originally intended to be temporary'\n"
                    "- First hop: confirms temporary structure but not demolition reason\n"
                    "- First second-hop: shows 1909 demolition plan but not preservation reason\n"
                    "- Missing: why demolition was canceled\n"
                    "- Alternative entities: Gustave Eiffel, military use\n"
                    "- Query: 'military significance Eiffel Tower 1909'\n\n"
                    
                    "Example 3 (Query):\n"
                    "Claim: 'The moon landing occurred in 1969'\n"
                    "- First hop: confirms year but not mission name\n"
                    "- First second-hop: shows Apollo program but not specific mission\n"
                    "- Missing: mission designation\n"
                    "- Alternative entities: NASA, 1969\n"
                    "- Query: 'NASA mission name moon landing 1969'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Second alternative second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve second second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query or stop",
                "step_type": "llm",
                "aim": "Determine if combined evidence is sufficient OR generate final query",
                "stage_action": (
                    "Analyze ALL retrieved passages (first-hop and both second-hop paths) to verify the claim. "
                    "If ALL claim components are verified, output 'SUFFICIENT'. "
                    "Otherwise, generate a precise search query for the missing evidence. "
                    "Output ONLY the query or 'SUFFICIENT', no additional text."
                ),
                "reasoning_questions": (
                    "1. Enumerate EXACTLY which gold document titles remain missing\n"
                    "2. What UNIQUE entity from combined evidence can retrieve each missing document?\n"
                    "3. How to phrase the most targeted query avoiding all previous terms?\n"
                    "4. If sufficient, list all verified components with supporting passage IDs"
                ),
                "example_reasoning": (
                    "Example 1 (Sufficient):\n"
                    "Claim: 'Water boils at 100°C at sea level'\n"
                    "- First hop: confirms boiling point at standard pressure\n"
                    "- Path1: shows Celsius scale definition\n"
                    "- Path2: confirms sea level pressure standard\n"
                    "- ALL elements verified → Output: 'SUFFICIENT'\n\n"
                    
                    "Example 2 (Query):\n"
                    "Claim: 'Marie Curie won two Nobel Prizes'\n"
                    "- First hop: confirms two prizes but not years\n"
                    "- Path1: shows 1903 Physics prize details\n"
                    "- Path2: shows 1911 Chemistry prize nomination\n"
                    "- Missing: exact year of Chemistry prize\n"
                    "- Critical gap: 1911 prize year confirmation\n"
                    "- Query: 'Marie Curie Nobel Chemistry prize year'\n\n"
                    
                    "Example 3 (Query):\n"
                    "Claim: 'The human genome has approximately 3 billion base pairs'\n"
                    "- First hop: confirms base pair count\n"
                    "- Path1: shows sequencing project completion date\n"
                    "- Path2: describes genome assembly method\n"
                    "- Missing: which organism's genome (human vs. others)\n"
                    "- Critical gap: explicit 'human' specification\n"
                    "- Query: 'human genome project base pair count specification'"
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
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }