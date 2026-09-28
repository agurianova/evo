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
            # Step 2: Analyze first hop and generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify key missing evidence from first-hop passages and generate a comprehensive search query that covers multiple evidence paths.",
                "stage_action": (
                    "Read the retrieved passages and analyze what evidence is needed to verify the claim. Follow this checklist: "
                    "1) List all evidence required to verify the claim "
                    "2) Check which evidence was found in retrieved passages "
                    "3) Identify exactly what's missing. "
                    "Generate a search query that covers 2-3 distinct ways the missing evidence might be described, using OR to combine terms. "
                    "Output format: ONLY the search query in plain text without quotes, explanations, or line breaks. "
                    "GOOD example: 'term1 OR term2 OR term3' "
                    "BAD example: 'Here's my query: term1 OR term2'"
                ),
                "reasoning_questions": (
                    "What specific facts or evidence are missing to verify the claim based on the first-hop passages? "
                    "What are 2-3 distinct ways this missing evidence might be described or related to known entities? "
                    "How can you combine these into one effective query using OR operators?"
                ),
                "example_reasoning": (
                    "The claim states that 'X causes Y'. The first-hop passages mention X and Y but do not confirm a causal link. "
                    "Missing evidence is confirmation of causation between X and Y. This might be described as 'X causes Y', 'X leads to Y', or 'X is a risk factor for Y'. "
                    "Query: 'X causes Y' OR 'X leads to Y' OR 'X is a risk factor for Y'"
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
                "aim": "Refine search based on previous results to identify and retrieve the next critical evidence.",
                "stage_action": (
                    "Review the claim and all retrieved passages from previous hops. Follow this checklist: "
                    "1) List all evidence required to verify the claim "
                    "2) Check which evidence was found in retrieved passages "
                    "3) Identify exactly what's missing. "
                    "Generate a search query that covers 2-3 distinct ways the missing evidence might be described, using OR to combine terms. "
                    "Output format: ONLY the search query in plain text without quotes, explanations, or line breaks. "
                    "GOOD example: 'term1 OR term2 OR term3' "
                    "BAD example: 'Next query: term1 OR term2'"
                ),
                "reasoning_questions": (
                    "What evidence was found by previous queries? What is still missing? "
                    "What are 2-3 alternative formulations for the missing evidence? "
                    "How can the next query be formulated to cover the missing evidence while avoiding redundant retrieval?"
                ),
                "example_reasoning": (
                    "Previous queries retrieved documents about X and Y but not Z. Missing evidence is Z (a critical component). "
                    "Z might be described as 'Z' or 'W' in sources. "
                    "Query: 'Y AND (Z OR W)'")
                ,
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
                "aim": "Identify the final missing piece after three hops and generate a comprehensive search query.",
                "stage_action": (
                    "Review the claim and all retrieved passages from previous hops. Follow this checklist: "
                    "1) List all evidence required to verify the claim "
                    "2) Check which evidence was found in retrieved passages "
                    "3) Identify exactly what's missing. "
                    "Generate a search query that covers 2-3 distinct ways the missing evidence might be described, using OR to combine terms. "
                    "Output format: ONLY the search query in plain text without quotes, explanations, or line breaks. "
                    "GOOD example: 'term1 OR term2 OR term3' "
                    "BAD example: 'Final query attempt: term1 OR term2'"
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "What are 2-3 alternative ways this evidence might be described? "
                    "How can you formulate a query that maximizes the chance of retrieving it?"
                ),
                "example_reasoning": (
                    "We have evidence for A, B, and C, but the claim requires confirmation of D. "
                    "D might be referred to as 'D' or 'E' in sources. "
                    "Query: 'A [D] B' OR 'A [E] B'")
                ,
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