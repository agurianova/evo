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
            # Step 2: Analyze first hop and generate second-hop query with evidence description
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify key facts from first-hop passages and determine critical missing evidence for verification, generating a query that covers multiple evidence paths.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to the claim. Identify critical missing information for verification. For each missing piece, describe what specific information is missing and how it relates to the claim. Generate a search query that includes at least two distinct alternative formulations for the missing evidence, connected by OR. "
                    "WARNING: Your response must contain ONLY the search query string. Any additional text (including explanations, bullet points, or line breaks) will cause the retrieval to fail. Format: 'term1 OR term2 OR ...'"
                ),
                "reasoning_questions": (
                    "What specific facts or evidence are missing to verify the claim based on the first-hop passages? "
                    "For each missing piece, describe: (1) what specific information is missing, (2) how it relates to the claim. "
                    "What are at least two distinct ways this missing evidence might be described in sources? "
                    "Before generating the query, list all required evidence pieces and verify against the retrieved passages to ensure no gaps are missed. "
                    "How can you combine the alternative formulations into one effective query using OR?"
                ),
                "example_reasoning": (
                    "The claim states that 'X causes Y'. The first-hop passages mention X and Y but do not confirm a causal link. "
                    "The missing evidence is the causal relationship between X and Y. This might be described as 'X causes Y' or 'X is a risk factor for Y'. "
                    "Therefore, the query is: 'X causes Y' OR 'X is a risk factor for Y'"
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
                    "Review the original claim, the first-hop passages (step1), and the second-hop passages (step3). "
                    "Identify what evidence was found and what is still missing. For each missing piece, describe what specific information is missing and how it relates to the claim. "
                    "Generate a search query that includes at least two distinct alternative formulations for the missing evidence, connected by OR. "
                    "WARNING: Your response must contain ONLY the search query string. Any additional text (including explanations, bullet points, or line breaks) will cause the retrieval to fail. Format: 'term1 OR term2 OR ...'"
                ),
                "reasoning_questions": (
                    "What evidence was found in the first-hop passages (step1)? What evidence was found in the second-hop passages (step3)? What is still missing? "
                    "For each missing piece, describe: (1) what specific information is missing, (2) how it relates to the claim. "
                    "What are at least two distinct ways this missing evidence might be described in sources? "
                    "Before generating the query, list all required evidence pieces and verify against the retrieved passages to ensure no gaps are missed. "
                    "How can you formulate a query that covers the missing evidence without redundant retrieval?"
                ),
                "example_reasoning": (
                    "The first-hop passages (step1) retrieved documents about X but not Y. The second-hop passages (step3) retrieved documents about Y but not Z. "
                    "The missing evidence is Z (a specific attribute of Y). This might be described as 'Z' or 'W'. "
                    "Therefore, the query is: 'Y AND (Z OR W)'"
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
                    "Review the original claim and the retrieved passages from the first-hop (step1), second-hop (step3), and third-hop (step5). "
                    "Identify the last critical piece of evidence needed. For this missing piece, describe what specific information is missing and how it relates to the claim. "
                    "Generate a search query that includes at least two distinct alternative formulations for the missing evidence, connected by OR. "
                    "WARNING: Your response must contain ONLY the search query string. Any additional text (including explanations, bullet points, or line breaks) will cause the retrieval to fail. Format: 'term1 OR term2 OR ...'"
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "Describe: (1) what specific information is missing, (2) how it relates to the claim. "
                    "What are at least two distinct ways this missing evidence might be described in sources? "
                    "Before generating the query, list the required evidence and verify against all retrieved passages to ensure no gaps are missed. "
                    "How can you formulate a query that maximizes the chance of retrieving it?"
                ),
                "example_reasoning": (
                    "We have evidence for A, B, and C from the first three hops, but the claim requires confirmation of D (a specific relation between A and B). "
                    "D might be referred to as 'D' or 'E' in sources. "
                    "Therefore, the query is: 'A [D] B' OR 'A [E] B'"
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