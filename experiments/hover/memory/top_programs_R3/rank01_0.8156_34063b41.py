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
                    "Read the retrieved passages and extract facts relevant to the claim. Identify specific missing information needed to verify the claim. "
                    "Generate a search query that covers multiple ways this missing evidence might be described. "
                    "IMPORTANT: Output ONLY the search query. Do not include any explanations, formatting, or additional text. "
                    "Example of GOOD output: 'X causes Y' OR 'X leads to Y' OR 'X is a risk factor for Y' "
                    "Example of BAD output: \"Here's my query: 'X causes Y' OR 'X leads to Y'\""
                ),
                "reasoning_questions": (
                    "What specific facts or evidence are missing to verify the claim based on the first-hop passages? "
                    "What are 2-3 distinct ways this missing evidence might be described in reliable sources? "
                    "How can you combine these into one effective query using OR operators? "
                    "Checklist: 1) What evidence has been found? 2) What evidence is still missing? 3) How can we search for the missing evidence?"
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
            # Step 4: Analyze first+second hops with query refinement
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Refine search based on previous results to identify and retrieve the next critical evidence.",
                "stage_action": (
                    "Review all retrieved passages from previous queries. Identify what evidence was found and what is still missing. "
                    "Write a search query for the next hop that addresses remaining gaps, using logical operators for diversity. "
                    "IMPORTANT: Output ONLY the search query. Do not include any explanations, formatting, or additional text. "
                    "Example of GOOD output: 'Y AND (Z OR W)' "
                    "Example of BAD output: \"Next query: 'Y AND (Z OR W)'\""
                ),
                "reasoning_questions": (
                    "What evidence was found by the previous queries? What is still missing? "
                    "What are 2-3 alternative ways to describe the missing evidence? "
                    "How can the next query be formulated to cover the missing evidence while avoiding redundant retrieval? "
                    "Checklist: 1) What evidence has been found? 2) What evidence is still missing? 3) How can we search for the missing evidence?"
                ),
                "example_reasoning": (
                    "The first query retrieved documents about X but not Y. The second query retrieved documents about Y but not Z. "
                    "Z might be described as 'Z' or 'W'. "
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
                "aim": "Identify the final missing piece after three hops and generate a comprehensive search query.",
                "stage_action": (
                    "Review all retrieved passages, the original claim, and identify the last critical piece of evidence needed. "
                    "Write a search query that covers multiple ways it might be described. "
                    "The query may include multiple terms connected by OR to cover alternative paths. "
                    "IMPORTANT: Output ONLY the search query. Do not include any explanations, formatting, or additional text. "
                    "Example of GOOD output: 'A [D] B' OR 'A [E] B' "
                    "Example of BAD output: \"Final query: 'A [D] B' OR 'A [E] B'\""
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "What are alternative ways this evidence might be described? "
                    "How can you formulate a query that maximizes the chance of retrieving it? "
                    "Checklist: 1) What evidence has been found? 2) What evidence is still missing? 3) How can we search for the missing evidence?"
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