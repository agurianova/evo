def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop evidence retrieval for claim verification. Always output search queries concisely and without extra text. When generating queries, use specific entities and relationships from the evidence to form precise queries. Avoid vague terms. When summarizing evidence, be precise and extract only relevant facts.",
        "steps": [
            # Step 1: First-hop retrieval (upgraded to deep)
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
            # Step 2: Summarize first-hop evidence (enhanced)
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "1. What is the claim being verified? 2. Which facts in the retrieved passages are directly relevant to the claim? 3. Are there any contradictions or ambiguities in the evidence? 4. What key entities and dates are mentioned that might be useful for further verification?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Passages:\n"
                    "[1] Eiffel Tower | Construction of the Eiffel Tower began in January 1887.\n"
                    "[2] Paris landmarks | The Eiffel Tower was completed in 1889.\n"
                    "Summary: Construction of the Eiffel Tower began in January 1887 and was completed in 1889."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (enhanced with structured guidance)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, identify the key entities and relationships that require further verification. "
                    "Formulate a precise search query using specific terms from the evidence to find the missing information.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "1. What is the claim? 2. What evidence has been found in the first hop? 3. What specific information is still missing to verify the claim? 4. What are the key entities and relationships that should be in the query?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop evidence: Construction began in January 1887.\n"
                    "Missing: The completion date.\n"
                    "Query: Eiffel Tower completion date\n\n"
                    "Example 2:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in Chemistry.'\n"
                    "First-hop evidence: Marie Curie won the Nobel Prize in Physics in 1903 and in Chemistry in 1911.\n"
                    "Missing: The claim states two in Chemistry, but evidence shows one in Physics and one in Chemistry.\n"
                    "Query: Marie Curie Nobel Prize categories"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deeper search)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence (enhanced)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "1. What is the claim being verified? 2. Which facts in the retrieved passages are directly relevant to the claim? 3. Are there any contradictions or ambiguities in the evidence? 4. What key entities and dates are mentioned that might be useful for further verification?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "Passages:\n"
                    "[1] Eiffel Tower | The Eiffel Tower's height is 300 meters without antennas.\n"
                    "[2] Paris landmarks | Antennas add 24 meters to the Eiffel Tower's height.\n"
                    "Summary: The Eiffel Tower is 300 meters tall without antennas, and antennas add 24 meters."
                ),
                "dependencies": [4],
            },
            # Step 6: Combine evidence and identify gaps (enhanced)
            {
                "number": 6,
                "title": "Combine evidence and identify gaps",
                "step_type": "llm",
                "aim": "Combine evidence and identify remaining gaps.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (step2) and the second-hop evidence summary (step5) to form a unified evidence summary. "
                    "Then, list any remaining gaps or ambiguities that need to be resolved for claim verification."
                ),
                "reasoning_questions": "1. What is the claim? 2. What evidence has been gathered from the first and second hops? 3. Is the evidence sufficient to verify the claim? 4. If not, what specific information is still missing?",
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "First-hop summary: The Eiffel Tower's height is 300 meters without antennas.\n"
                    "Second-hop summary: Antennas add 24 meters to the height.\n"
                    "Unified summary: The Eiffel Tower is 300 meters tall without antennas, and antennas add 24 meters.\n"
                    "Remaining gaps: It is unclear whether the standard height measurement includes antennas."
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query (enhanced with structured guidance)
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Review the combined evidence from the first two hops. Identify any ambiguities, contradictions, or missing specifics. "
                    "Formulate a precise search query targeting the most critical gap for verification.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "1. What is the claim? 2. What evidence has been gathered so far? 3. What specific information is still missing to resolve ambiguities? 4. What are the key entities and relationships for the query?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "Combined evidence: The Eiffel Tower is 300 meters without antennas.\n"
                    "Missing: Whether standard height includes antennas.\n"
                    "Query: Eiffel Tower standard height measurement\n\n"
                    "Example 2:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in Chemistry.'\n"
                    "Combined evidence: Marie Curie won one Nobel Prize in Chemistry (1911) and one in Physics (1903).\n"
                    "Missing: Clarification that she did not win two in Chemistry.\n"
                    "Query: Marie Curie Nobel Prize Chemistry count"
                ),
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval (deeper search)
            {
                "number": 8,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Gap analysis with raw passages (enhanced)
            {
                "number": 9,
                "title": "Gap analysis",
                "step_type": "llm",
                "aim": "Determine if evidence is sufficient and generate fourth-hop query if needed.",
                "stage_action": (
                    "First, create a concise summary of the first-hop passages (step1), second-hop passages (step4), and third-hop passages (step8). "
                    "Then, integrate these summaries to form a complete evidence base for the claim. "
                    "If the claim can be verified as true or false with the complete evidence, output the main subject of the claim (e.g., for 'The Eiffel Tower was built in 1887', output 'Eiffel Tower'). "
                    "Otherwise, identify the single most critical missing piece of information and write a precise search query to find it.\n"
                    "Provide ONLY the search query or the main subject (if no gap), no additional text."
                ),
                "reasoning_questions": "1. What is the core claim being verified? 2. What evidence has been gathered from the first-hop, second-hop, and third-hop passages? 3. Is there any ambiguity or contradiction in the evidence? 4. What specific fact is still missing that would allow a definitive verification?",
                "example_reasoning": (
                    "Case 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages: [1] Eiffel Tower | Construction began in January 1887. ... \n"
                    "Second-hop passages: [1] Eiffel Tower construction | The tower was completed in 1889. ... \n"
                    "Third-hop passages: [1] Eiffel Tower completion | Completed on March 31, 1889. ... \n"
                    "Analysis: The claim is false because 'built in 1887' implies completion in 1887, but it was completed in 1889.\n"
                    "Output: Eiffel Tower\n\n"
                    "Case 2:\n"
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "First-hop passages: [1] Eiffel Tower | Height is 300 meters without antennas. ... \n"
                    "Second-hop passages: [1] Eiffel Tower height | Antennas add 24 meters. ... \n"
                    "Third-hop passages: [1] Eiffel Tower specifications | Standard height excludes antennas. ... \n"
                    "Analysis: The claim is true for the standard measurement (excludes antennas).\n"
                    "Output: Eiffel Tower\n\n"
                    "Case 3:\n"
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "First-hop passages: [1] Eiffel Tower | Height is 300 meters without antennas. ... \n"
                    "Second-hop passages: [1] Eiffel Tower height | Antennas add 24 meters. ... \n"
                    "Third-hop passages: [1] Eiffel Tower temperature | Height varies with temperature. ... \n"
                    "Analysis: We still don't know if the standard height includes antennas.\n"
                    "Output: Eiffel Tower standard height measurement"
                ),
                "dependencies": [1, 4, 8],
            },
            # Step 10: Fourth-hop retrieval (deeper search)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }