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
                "aim": "Identify key facts from first-hop passages and determine critical missing evidence for verification, generating a query that covers multiple evidence paths with BM25-aware expansion.",
                "stage_action": (
                    "Read the retrieved passages and extract facts relevant to the claim. Identify specific missing information needed to verify the claim. "
                    "Generate a search query that covers multiple ways this missing evidence might be described, including common synonyms and related terms that might appear in Wikipedia abstracts (e.g., for 'heart attack', consider 'myocardial infarction'). "
                    "Use OR to combine these variations. "
                    "IMPORTANT: Output ONLY the search query. Do not include any explanations, formatting, or additional text. "
                    "Example of GOOD output: 'X causes Y' OR 'X leads to Y' OR 'X is a risk factor for Y' OR 'synonym_X causes synonym_Y' "
                    "Example of BAD output: \"Here's my query: 'X causes Y' OR 'X leads to Y'\""
                ),
                "reasoning_questions": (
                    "What specific facts or evidence are missing to verify the claim based on the first-hop passages? "
                    "What are 2-3 distinct ways this missing evidence might be described in reliable sources? "
                    "What synonyms or related terms (common in Wikipedia) might describe the key concepts in this missing evidence? "
                    "How can you combine these into one effective query using OR operators? "
                    "Checklist: 1) What are the main entities and relations in the claim? 2) What evidence about these is found in the first-hop passages? "
                    "3) What specific missing information is critical for verification? 4) What synonyms or related terms might describe this missing evidence in Wikipedia?"
                ),
                "example_reasoning": (
                    "The claim states that 'smoking causes lung cancer'. The first-hop passages mention smoking and lung cancer but do not confirm a causal link. "
                    "This might be described as 'smoking causes lung cancer', 'tobacco use leads to lung cancer', or 'smoking is a risk factor for lung cancer'. "
                    "Also, consider synonyms: 'tobacco smoking' for smoking and 'pulmonary carcinoma' for lung cancer. "
                    "Therefore, the query should be 'smoking causes lung cancer' OR 'tobacco use leads to lung cancer' OR 'smoking is a risk factor for lung cancer' OR 'tobacco smoking causes pulmonary carcinoma'."
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
                "aim": "Refine search based on previous results to identify and retrieve the next critical evidence with BM25-aware expansion.",
                "stage_action": (
                    "Review all retrieved passages from previous queries. Identify what evidence was found and what is still missing. "
                    "Write a search query for the next hop that addresses remaining gaps, using logical operators for diversity and including synonyms/related terms from Wikipedia. "
                    "IMPORTANT: Output ONLY the search query. Do not include any explanations, formatting, or additional text. "
                    "Example of GOOD output: 'Y AND (Z OR W OR synonym_Z)' "
                    "Example of BAD output: \"Next query: 'Y AND (Z OR W)'\""
                ),
                "reasoning_questions": (
                    "What evidence was found by the previous queries? What is still missing? "
                    "What are 2-3 alternative ways to describe the missing evidence? "
                    "What synonyms or related terms (common in Wikipedia) might describe the key concepts in the missing evidence? "
                    "How can the next query be formulated to cover the missing evidence while avoiding redundant retrieval? "
                    "Checklist: 1) What new evidence was found in the second hop? 2) How does it connect to the first-hop evidence? "
                    "3) What specific gap remains that must be filled for verification? 4) What synonyms or related terms might describe this gap in Wikipedia?"
                ),
                "example_reasoning": (
                    "The first query retrieved documents about smoking but not lung cancer. The second query retrieved documents about lung cancer but not the causal link to smoking. "
                    "The causal link might be described as 'smoking causes lung cancer', 'tobacco use leads to lung cancer', or 'smoking is a risk factor for lung cancer'. "
                    "Also, consider 'cigarette smoking' and 'respiratory cancer'. "
                    "Therefore, the next query should be 'smoking causes lung cancer' OR 'tobacco use leads to lung cancer' OR 'smoking is a risk factor for lung cancer' OR 'cigarette smoking causes respiratory cancer'."
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
                "aim": "Identify the final missing piece after three hops and generate a comprehensive search query with BM25-aware expansion.",
                "stage_action": (
                    "Review all retrieved passages, the original claim, and identify the last critical piece of evidence needed. "
                    "Write a search query that covers multiple ways it might be described, including synonyms and related terms from Wikipedia. "
                    "The query may include multiple terms connected by OR to cover alternative paths. "
                    "IMPORTANT: Output ONLY the search query. Do not include any explanations, formatting, or additional text. "
                    "Example of GOOD output: 'A [D] B' OR 'A [E] B' OR 'synonym_A [D] synonym_B' "
                    "Example of BAD output: \"Final query: 'A [D] B' OR 'A [E] B'\""
                ),
                "reasoning_questions": (
                    "What is the absolute last piece of evidence required to verify the claim? "
                    "What are alternative ways this evidence might be described? "
                    "What synonyms or related terms (common in Wikipedia) might describe the key concepts in this evidence? "
                    "How can you formulate a query that maximizes the chance of retrieving it? "
                    "Checklist: 1) What evidence has been gathered so far? 2) What is the single most critical missing piece for verification? "
                    "3) How can we formulate a query that targets only this missing piece? 4) What synonyms or related terms might describe this critical piece in Wikipedia?"
                ),
                "example_reasoning": (
                    "We have evidence for smoking, lung cancer, and risk factors, but the claim requires confirmation of causation. "
                    "Causation might be referred to as 'causes', 'leads to', 'results in', or 'is a direct cause of'. "
                    "Also, consider 'tobacco smoke' and 'pulmonary neoplasms'. "
                    "Therefore, the query should be 'smoking causes lung cancer' OR 'tobacco use leads to lung cancer' OR 'smoking results in pulmonary neoplasms'."
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