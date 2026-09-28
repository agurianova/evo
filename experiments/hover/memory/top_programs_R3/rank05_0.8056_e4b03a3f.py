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
                "aim": "Identify key facts from first-hop passages and determine critical missing evidence for verification, generating a query that covers multiple evidence paths.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to the claim. Identify specific missing evidence pieces required to verify the claim. "
                    "Generate a search query that covers at least two distinct formulations of the missing evidence using OR logic. "
                    "WARNING: Output ONLY the search query. Any additional text will break the retrieval system."
                ),
                "reasoning_questions": (
                    "What specific facts or evidence are missing to verify the claim based on the first-hop passages? "
                    "What are 2-3 distinct ways this missing evidence might be described or related to known entities? "
                    "How can you combine these into one effective query using OR to maximize coverage?"
                ),
                "example_reasoning": (
                    "The claim states that 'X causes Y'. The first-hop passages mention X and Y but do not confirm a causal link. "
                    "This might be described as 'X causes Y', 'X leads to Y', or 'X is a risk factor for Y'. "
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
            # Step 4: Analyze first+second hops
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Refine search based on previous evidence to identify and retrieve the next critical evidence.",
                "stage_action": (
                    "Review the passages retrieved from the first two queries. Identify what evidence was found and what is still missing. "
                    "Generate a search query that covers at least two distinct formulations of the remaining missing evidence using OR logic. "
                    "WARNING: Output ONLY the search query. Any additional text will break the retrieval system."
                ),
                "reasoning_questions": (
                    "What evidence was found by the first query? What evidence was found by the second query? What is still missing? "
                    "What are 2-3 alternative ways the missing evidence might be described? "
                    "How can you formulate a query that covers these alternatives while avoiding redundant retrieval?"
                ),
                "example_reasoning": (
                    "The first query retrieved documents about X but not Y. The second query retrieved documents about Y but not Z. "
                    "Z might be described as 'Z' or 'W'. "
                    "Therefore, the query should be 'Y AND (Z OR W)'."
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
            # Step 6: Analyze all hops
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing piece after three hops and generate a comprehensive search query.",
                "stage_action": (
                    "Review all retrieved passages from the first three hops and the original claim. "
                    "Identify the last critical piece of evidence needed and generate a search query that covers at least two distinct formulations using OR logic. "
                    "WARNING: Output ONLY the search query. Any additional text will break the retrieval system."
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "What are 2-3 alternative ways this evidence might be described or related concepts that should be included? "
                    "How can you formulate a query that maximizes the chance of retrieving it?"
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