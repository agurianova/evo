def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Always prioritize recall for multi-hop claims. Focus on generating precise search queries to find missing evidence. Maximize coverage of relevant documents.",
        "steps": [
            # Step 1: First-hop retrieval with deep recall
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Generate second-hop query with reasoning scaffolds
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing evidence gaps and generate precise search query for second hop",
                "stage_action": (
                    "Analyze all retrieved passages to determine what specific evidence is missing for claim verification. "
                    "Formulate a concise, targeted search query to find the missing information. "
                    "Output ONLY the search query text, no additional commentary or formatting."
                ),
                "reasoning_questions": (
                    "1. What key fact or relationship is missing from current evidence to verify the claim?\n"
                    "2. Which entities/dates/locations need further verification?\n"
                    "3. How can we phrase a query that balances precision and recall for the missing element?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in 1919 and ratified in 1920.'\n"
                    "Current evidence: Passages confirm signing date (June 28, 1919) but omit ratification timeline.\n"
                    "Missing: specific ratification date and process.\n"
                    "Query: 'Treaty of Versailles ratification date and procedure'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval with deep recall
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate third-hop query with reasoning scaffolds
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining evidence gaps using all available passages and generate precise third-hop query",
                "stage_action": (
                    "Integrate evidence from first and second hop passages to identify residual verification gaps. "
                    "Create a targeted search query addressing the most critical missing information. "
                    "Output ONLY the search query text, no additional commentary or formatting."
                ),
                "reasoning_questions": (
                    "1. What verification gaps persist after combining all evidence so far?\n"
                    "2. Which missing element has the highest impact on claim verification?\n"
                    "3. How can we refine the query to avoid previously retrieved information?"
                ),
                "example_reasoning": (
                    "Claim: 'Mount Everest's height was first measured as 29,002 ft in 1856.'\n"
                    "Current evidence: Confirms 1856 survey and height measurement method but lacks original calculation details.\n"
                    "Missing: specific trigonometric calculations used in 1856 survey.\n"
                    "Query: 'Great Trigonometrical Survey 1856 Everest calculation method'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Third-hop retrieval with deep recall
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Generate fourth-hop query with reasoning scaffolds
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify residual verification gaps using all evidence and generate precise fourth-hop query",
                "stage_action": (
                    "Synthesize evidence from first three hops to pinpoint remaining verification gaps. "
                    "Formulate a highly targeted query for the most critical missing evidence. "
                    "Output ONLY the search query text, no additional commentary or formatting."
                ),
                "reasoning_questions": (
                    "1. What specific contradiction or ambiguity remains unverified?\n"
                    "2. Which missing source would provide definitive evidence?\n"
                    "3. How can we phrase a query using domain-specific terminology for precision?"
                ),
                "example_reasoning": (
                    "Claim: 'The Rosetta Stone was discovered by French soldiers in 1799.'\n"
                    "Current evidence: Confirms 1799 discovery near Rosetta but omits discoverer's name and unit.\n"
                    "Missing: specific French military unit and officer responsible.\n"
                    "Query: 'Rosetta Stone discoverer French military unit 1799'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Fourth-hop retrieval with deep recall
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Generate fifth-hop query with reasoning scaffolds
            {
                "number": 8,
                "title": "Generate fifth-hop query",
                "step_type": "llm",
                "aim": "Identify final verification gaps using all evidence and generate precise fifth-hop query",
                "stage_action": (
                    "Analyze complete evidence set to identify any remaining verification gaps. "
                    "Create a last-resort query targeting the most critical missing evidence. "
                    "Output ONLY the search query text, no additional commentary or formatting."
                ),
                "reasoning_questions": (
                    "1. What single piece of evidence would definitively verify or refute the claim?\n"
                    "2. Which authoritative source would contain this information?\n"
                    "3. How can we phrase a query to bypass common misconceptions?"
                ),
                "example_reasoning": (
                    "Claim: 'Shakespeare's play Hamlet was first performed in 1600.'\n"
                    "Current evidence: Confirms composition circa 1599-1601 but lacks first performance records.\n"
                    "Missing: documented evidence of earliest known performance.\n"
                    "Query: 'Hamlet first performance documented evidence Globe Theatre'"
                ),
                "dependencies": [1, 3, 5, 7],
            },
            # Step 9: Fifth-hop retrieval with deep recall
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
        ],
    }