def entrypoint():
    return {
        "system_prompt": "You are a fact-checking assistant. Your goal is to maximize the retrieval of supporting evidence for claim verification by generating precise search queries and analyzing evidence across multiple hops. Always prioritize finding all relevant gold standard documents.",
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
            # Step 2: Analyze first hop and generate second-hop query with evidence typing
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify key facts from first-hop passages and determine critical missing evidence for verification, generating a query that covers multiple evidence paths.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to the claim. Identify each critical missing piece of evidence. "
                    "For each missing piece, generate at least two distinct alternative descriptions. "
                    "Write a search query that combines these descriptions using OR. "
                    "Provide ONLY the search query, no additional text. "
                    "Example of good output: 'X causes Y' OR 'X leads to Y'. "
                    "Example of bad output: 'The query is: X causes Y OR X leads to Y'."
                ),
                "reasoning_questions": (
                    "What specific facts or evidence are missing to verify the claim based on the first-hop passages? "
                    "For each missing piece, list at least two distinct ways it might be described. "
                    "How can you combine these into one effective query using OR? "
                    "Verify that each required piece of evidence is not already in the passages."
                ),
                "example_reasoning": (
                    "The claim states that 'X causes Y'. The first-hop passages mention X and Y but do not confirm a causal link. "
                    "The missing evidence might be described as 'X causes Y', 'X leads to Y', or 'X is a risk factor for Y'. "
                    "Therefore, the query should be 'X causes Y' OR 'X leads to Y' OR 'X is a risk factor for Y'."
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
            # Step 4: Analyze first+second hops with query refinement
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Refine search based on previous queries and results to identify and retrieve the next critical evidence.",
                "stage_action": (
                    "Review the first-hop passages (step1) and the second-hop passages (step3). "
                    "Identify what evidence was found and what is still missing. "
                    "For each missing piece, generate at least two distinct alternative descriptions. "
                    "Write a search query for the next hop that addresses remaining gaps, using OR to combine alternative descriptions. "
                    "Provide ONLY the search query, no additional text. "
                    "Example of good output: 'Y AND (Z OR W)'. "
                    "Example of bad output: 'Next query: Y AND (Z OR W)'."
                ),
                "reasoning_questions": (
                    "What evidence was found in the first-hop passages (step1)? "
                    "What evidence was found in the second-hop passages (step3)? "
                    "What is still missing? "
                    "For each missing piece, list at least two distinct ways it might be described. "
                    "How can you combine these into a query that avoids redundant retrieval?"
                ),
                "example_reasoning": (
                    "The first-hop passages retrieved documents about X but not Y. "
                    "The second-hop passages retrieved documents about Y but not Z. "
                    "The missing evidence might be described as 'Z' or 'W'. "
                    "Therefore, the next query should be 'Y AND (Z OR W)'."
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
            # Step 6: Analyze all hops with final refinement
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing piece after three hops and generate a comprehensive search query that covers alternative formulations.",
                "stage_action": (
                    "Review all retrieved passages from the first three hops (steps 1, 3, 5). "
                    "Identify the last critical piece of evidence needed. "
                    "Generate at least two distinct alternative descriptions for it. "
                    "Write a search query that covers these descriptions using OR. "
                    "Provide ONLY the search query, no additional text. "
                    "Example of good output: 'A [D] B' OR 'A [E] B'. "
                    "Example of bad output: 'Final query: A [D] B OR A [E] B'."
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "For this missing piece, list at least two distinct ways it might be described. "
                    "Are there related concepts that should be included? "
                    "How can you formulate a query that maximizes the chance of retrieving it using OR?"
                ),
                "example_reasoning": (
                    "We have evidence for A, B, and C, but the claim requires confirmation of D. "
                    "D might be referred to as 'D' or 'E' in sources. "
                    "Therefore, the query should be 'A [D] B' OR 'A [E] B'."
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