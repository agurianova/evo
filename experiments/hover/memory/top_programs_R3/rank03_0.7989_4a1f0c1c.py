def entrypoint():
    return {
        "system_prompt": (
            "You are a fact-checking assistant tasked with verifying claims by retrieving supporting evidence from Wikipedia. "
            "Your goal is to maximize the retrieval coverage of gold-standard supporting documents. "
            "At each query generation step, focus on identifying the most critical missing information and formulate precise search queries. "
            "When generating queries, consider using OR operators for alternative terms if the evidence gap is ambiguous."
        ),
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
            # Step 2: Generate second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information after the first retrieval and generate a precise search query for the second hop.",
                "stage_action": (
                    "Analyze the retrieved passages from the first hop to determine what specific evidence is still missing to verify the claim. "
                    "Formulate a concise and effective search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What key fact or entity mentioned in the claim is not covered by the first-hop passages?\n"
                    "2. What specific question needs to be answered to bridge the gap between the claim and the current evidence?"
                ),
                "example_reasoning": (
                    "The claim states 'The Eiffel Tower was built in 1887'. The first-hop passages confirm the construction started in 1887 but do not mention the completion year. "
                    "To verify the claim, we need to know if the tower was completed in 1887. Missing evidence: completion year of the Eiffel Tower.\n"
                    "Query: 'Eiffel Tower completion year'"
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
            # Step 4: Generate third-hop query
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps after two hops and generate a targeted search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered from the first two retrieval hops, determine what specific information is still missing to verify the claim. "
                    "Formulate a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What evidence has been gathered so far and what does it confirm or refute?\n"
                    "2. What specific piece of information is still required to fully verify the claim?"
                ),
                "example_reasoning": (
                    "The claim is 'Marie Curie won two Nobel Prizes in Chemistry'. First hop: she won Nobel Prizes in Physics (1903) and Chemistry (1911). Second hop: confirms the Chemistry prize was for her work on radium and polonium. "
                    "However, the claim says 'two Nobel Prizes in Chemistry' but we found one in Physics and one in Chemistry. Missing evidence: clarification that she won one in Physics and one in Chemistry, not two in Chemistry.\n"
                    "Query: 'Marie Curie Nobel Prizes breakdown'"
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
            # Step 6: Generate fourth-hop query
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final gaps after three hops and generate a comprehensive search query for the fourth hop, using multi-term strategies if needed.",
                "stage_action": (
                    "After three retrieval hops, analyze the accumulated evidence to pinpoint any remaining uncertainties. "
                    "Generate a search query that casts a wide net to capture the final missing evidence, using OR operators for alternative phrasings or related concepts if necessary. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What is the precise gap that remains after reviewing all evidence?\n"
                    "2. What alternative terms or related concepts might help find the missing information?"
                ),
                "example_reasoning": (
                    "The claim: 'The human genome has 20,000-25,000 protein-coding genes'. First three hops: passages confirm the range but one says 20,500 and another 24,000. Missing: the exact current consensus number. "
                    "To capture different sources, we can search for multiple terms. Query: 'human genome protein-coding genes count OR number OR total'"
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