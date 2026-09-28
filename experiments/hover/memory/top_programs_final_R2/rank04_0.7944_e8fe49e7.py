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
            # Step 2: Generate primary second-hop query with entity extraction and fallback
            {
                "number": 2,
                "title": "Generate primary second-hop query",
                "step_type": "llm",
                "aim": "Identify key entities and critical missing fact to generate precise search query",
                "stage_action": (
                    "Analyze the claim and first-hop evidence. If evidence is empty, generate a query for the main entity. "
                    "Otherwise, identify key entities and the most critical missing fact, then generate a precise search query. "
                    "Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "1. What are the key entities in the claim? \n"
                    "2. What specific fact about these entities is missing from the evidence? \n"
                    "3. How can we formulate a domain-specific query for this missing fact? \n"
                    "4. If evidence is empty, what is the main entity of the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The mitochondria are the powerhouse of the cell.'\n"
                    "Evidence: [1] Mitochondrion | Organelle found in most eukaryotic cells.\n"
                    "Key entities: mitochondria, cell\n"
                    "Missing fact: function as energy producer\n"
                    "Query: 'mitochondria function chemical energy'")
                ,
                "dependencies": [1],
            },
            # Step 3: Generate alternative second-hop query with unconditional diversity
            {
                "number": 3,
                "title": "Generate alternative second-hop query",
                "step_type": "llm",
                "aim": "Identify distinct missing fact path and generate diverse query",
                "stage_action": (
                    "Analyze the claim and first-hop evidence to identify a missing fact providing a different verification path than step2's query. "
                    "Focus on distinct key entities or unverified aspects. Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "1. What are the key entities in the claim? \n"
                    "2. What specific missing fact differs from step2's focus? \n"
                    "3. How can we formulate a domain-specific query for this distinct fact?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919.'\n"
                    "Evidence: [1] Treaty of Versailles | Ended World War I, signed in Paris on June 28, 1919.\n"
                    "Distinct missing fact: signing location\n"
                    "Query: 'Treaty of Versailles signing location'")
                ,
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
                    "First, summarize all retrieved evidence (first-hop, primary/alternative second-hop) into verified facts and remaining gaps. "
                    "Then identify the most critical unverified claim component and output ONLY its search query string."
                ),
                "reasoning_questions": (
                    "1. What specific claim parts are verified by evidence? \n"
                    "2. What critical component remains unverified? \n"
                    "3. Which unverified component is most essential for claim verification? \n"
                    "4. How can we target only this gap without overlapping evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The mitochondria are the powerhouse of the cell.'\n"
                    "Evidence:\n"
                    "  [1] Mitochondrion | Organelle known as the powerhouse, produces ATP.\n"
                    "  [2] Cellular respiration | Occurs in mitochondria to produce ATP.\n"
                    "  [3] ATP | Energy currency produced by mitochondria.\n"
                    "Verified: Mitochondria produce ATP and are called powerhouse.\n"
                    "Gaps: Specific ATP production mechanism (e.g., oxidative phosphorylation)\n"
                    "Query: 'mitochondria ATP production mechanism'")
                ,
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