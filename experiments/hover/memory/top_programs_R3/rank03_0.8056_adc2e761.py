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
            # Step 2: Analyze first hop and generate second-hop query with dynamic gap analysis
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify key facts from first-hop passages and determine critical missing evidence for verification, generating a query that covers multiple evidence paths.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to the claim. Use the checklist to identify missing evidence and generate alternative descriptions. "
                    "Write a search query that covers the missing evidence by including at least two alternative formulations for each critical missing piece, connected by OR. "
                    "Your response must be ONLY the search query string, with no other text. Do not include any explanations, labels, or extra lines."
                ),
                "reasoning_questions": (
                    "Checklist:\n"
                    "1. List every piece of evidence required to verify the claim.\n"
                    "2. For each required piece, check if it is present in the first-hop passages.\n"
                    "3. Identify the missing pieces. For each missing piece, consider at least two alternative ways it might be described (e.g., different terms, related concepts).\n"
                    "4. How can you combine these alternative descriptions into one effective query using logical operators (OR, AND)?"
                ),
                "example_reasoning": (
                    "The claim requires evidence of causation between X and Y. First-hop passages do not confirm causation. "
                    "Missing evidence: causation relation. Alternative descriptions: 'causes', 'leads to', 'is a risk factor for'. "
                    "Search query: 'X causes Y' OR 'X leads to Y' OR 'X is a risk factor for Y'"
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
            # Step 4: Analyze first+second hops with optimized dependencies
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Refine search based on previous results to identify and retrieve the next critical evidence.",
                "stage_action": (
                    "Review the passages from the first and second hops. Use the checklist to identify missing evidence and generate alternative descriptions. "
                    "Write a search query that covers the missing evidence by including at least two alternative formulations for each critical missing piece, connected by OR. "
                    "Your response must be ONLY the search query string, with no other text. Do not include any explanations, labels, or extra lines."
                ),
                "reasoning_questions": (
                    "Checklist:\n"
                    "1. List every piece of evidence required to verify the claim.\n"
                    "2. For each required piece, check if it is present in the first-hop and second-hop passages.\n"
                    "3. Identify the missing pieces. For each missing piece, consider at least two alternative ways it might be described.\n"
                    "4. How can you formulate a query that covers the missing evidence while avoiding redundant retrieval, using logical operators for diversity?"
                ),
                "example_reasoning": (
                    "The first query retrieved documents about X but not Y. The second query retrieved documents about Y but not Z. "
                    "Missing evidence: Z (an attribute of Y). Alternative descriptions: 'Z', 'W'. "
                    "Search query: 'Y AND (Z OR W)'"
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
                    "Review all retrieved passages from the first three hops and the original claim. Use the checklist to identify the last critical missing piece and generate alternative descriptions. "
                    "Write a search query that covers the missing evidence by including at least two alternative formulations, connected by OR. "
                    "Your response must be ONLY the search query string, with no other text. Do not include any explanations, labels, or extra lines."
                ),
                "reasoning_questions": (
                    "Checklist:\n"
                    "1. List every piece of evidence required to verify the claim.\n"
                    "2. For each required piece, check if it is present in all retrieved passages so far.\n"
                    "3. Identify the last critical missing piece. Consider at least two alternative ways it might be described.\n"
                    "4. How can you formulate a query that maximizes the chance of retrieving it?"
                ),
                "example_reasoning": (
                    "We have evidence for A, B, and C, but the claim requires confirmation of D (a relation between A and B). "
                    "Alternative descriptions: 'D', 'E'. "
                    "Search query: 'A [D] B' OR 'A [E] B'"
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