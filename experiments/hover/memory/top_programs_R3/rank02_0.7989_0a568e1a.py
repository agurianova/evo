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
                    "Read the retrieved passages and extract facts relevant to the claim. Identify multiple critical missing information paths and write a search query that covers them using logical operators (e.g., OR, AND). "
                    "Classify missing evidence as entity, relation, or attribute. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific facts or evidence are missing to verify the claim based on the first-hop passages? "
                    "Classify each missing piece as: entity (a person, place, thing), relation (a connection between entities), or attribute (a property of an entity). "
                    "What are 2-3 distinct ways this missing evidence might be described or related to known entities? "
                    "How can you combine these into one effective query?"
                ),
                "example_reasoning": (
                    "The claim states that 'X causes Y'. The first-hop passages mention X and Y but do not confirm a causal link. "
                    "The missing evidence is a relation (causation) between X and Y. This might be described as 'X causes Y', 'X leads to Y', or 'X is a risk factor for Y'. "
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
                    "Review the first query (the claim), the second query you generated, and the passages retrieved from both queries. "
                    "Identify what evidence was found and what is still missing. Classify missing evidence as entity, relation, or attribute. "
                    "Write a search query for the next hop that addresses remaining gaps, using logical operators for diversity. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What evidence was found by the first query? What evidence was found by the second query? What is still missing? "
                    "Classify the missing evidence. How can the next query be formulated to cover the missing evidence while avoiding redundant retrieval? "
                    "Consider 2-3 alternative formulations for the missing evidence."
                ),
                "example_reasoning": (
                    "The first query (claim) retrieved documents about X but not Y. The second query retrieved documents about Y but not Z. "
                    "The missing evidence is Z (an attribute of Y). Z might be described as 'Z' or 'W'. "
                    "Therefore, the next query should be 'Y AND (Z OR W)'."
                ),
                "dependencies": [1, 2, 3],
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
                    "Review all retrieved passages from the first three hops, the original claim, and the queries you generated. "
                    "Identify the last critical piece of evidence needed, classify it, and write a search query that covers multiple ways it might be described. "
                    "The query may include multiple terms connected by OR to cover alternative paths. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "Classify it as entity, relation, or attribute. "
                    "Are there alternative ways this evidence might be described or related concepts that should be included? "
                    "How can you formulate a query that maximizes the chance of retrieving it?"
                ),
                "example_reasoning": (
                    "We have evidence for A, B, and C, but the claim requires confirmation of D (a relation between A and B). "
                    "D might be referred to as 'D' or 'E' in sources. "
                    "Therefore, the query should be 'A [D] B' OR 'A [E] B'."
                ),
                "dependencies": [1, 2, 3, 4, 5],
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