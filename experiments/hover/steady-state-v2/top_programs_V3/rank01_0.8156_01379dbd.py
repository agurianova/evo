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
            # Step 2: Summarize first-hop evidence (enhanced with guidance)
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "1. What is the core claim being verified?\n"
                    "2. What specific facts related to the claim are present in the first-hop passages?\n"
                    "3. Are there any ambiguities or missing details in the evidence that require further verification?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Passages: [1] Eiffel Tower | Construction began in January 1887.\n"
                    "Summary: Construction of the Eiffel Tower began in January 1887. However, the completion date is not mentioned, which is needed to verify if it was 'built in 1887'."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (enhanced with multi-case examples)
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
                "reasoning_questions": (
                    "1. What is the core claim?\n"
                    "2. What evidence has been gathered so far (from first-hop)?\n"
                    "3. What specific fact is still missing that would allow a definitive verification?\n"
                    "4. What are the key entities and relationships to use in the query?"
                ),
                "example_reasoning": (
                    "Case 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop evidence: Construction began in January 1887.\n"
                    "Missing: The completion date.\n"
                    "Query: Eiffel Tower completion date\n\n"
                    "Case 2:\n"
                    "Claim: 'Marie Curie won two Nobel Prizes in Physics.'\n"
                    "First-hop evidence: Marie Curie won the Nobel Prize in Physics in 1903 and the Nobel Prize in Chemistry in 1911.\n"
                    "Missing: The claim says 'two Nobel Prizes in Physics', but one was in Chemistry.\n"
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
            # Step 5: Summarize second-hop evidence (enhanced with guidance)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "1. What is the core claim being verified?\n"
                    "2. What new facts related to the claim are present in the second-hop passages?\n"
                    "3. How do these facts relate to the gaps identified in the first-hop evidence?\n"
                    "4. Are there still ambiguities or missing details that require further verification?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "First-hop summary: The Eiffel Tower's height is 300 meters without antennas.\n"
                    "Second-hop passages: [1] Eiffel Tower | The standard height measurement does not include the antennas.\n"
                    "Summary: The standard height measurement of the Eiffel Tower is 300 meters, which does not include the antennas. The claim does not specify if it includes antennas, so we need to know the common usage of the height figure."
                ),
                "dependencies": [4],
            },
            # Step 6: Combine evidence (enhanced with gap listing)
            {
                "number": 6,
                "title": "Combine evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (step2) with the second-hop evidence summary (step5). "
                    "Produce a unified evidence summary covering all relevant facts found so far. Then, explicitly list any unresolved gaps, "
                    "ambiguities, or missing specifics that remain for verifying the claim."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query (enhanced with multi-case examples)
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
                "reasoning_questions": (
                    "1. What is the core claim?\n"
                    "2. What evidence has been gathered from the first two hops?\n"
                    "3. What ambiguities or contradictions remain?\n"
                    "4. What is the single most critical missing piece of information for verification?\n"
                    "5. What specific terms will form the most precise query?"
                ),
                "example_reasoning": (
                    "Case 1:\n"
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "Combined evidence: The Eiffel Tower's height is 300 meters without antennas.\n"
                    "Ambiguity: The claim does not specify if it includes antennas.\n"
                    "Query: Eiffel Tower standard height measurement\n\n"
                    "Case 2:\n"
                    "Claim: 'Albert Einstein developed the theory of relativity in 1905.'\n"
                    "Combined evidence: Einstein published the special theory of relativity in 1905, but the general theory was developed later.\n"
                    "Ambiguity: The claim says 'the theory of relativity' without specifying which one.\n"
                    "Query: Albert Einstein theory of relativity publication year"
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
            # Step 9: Gap analysis (enhanced with raw passages and always outputs query)
            {
                "number": 9,
                "title": "Gap analysis",
                "step_type": "llm",
                "aim": "Review all evidence and generate fourth-hop query.",
                "stage_action": (
                    "Read all retrieved passages from the first hop (step1), second hop (step4), and third hop (step8). "
                    "Create a unified summary of all evidence. Always output a precise search query. "
                    "If the evidence is sufficient to verify the claim, output a query that is the main subject of the claim (e.g., the entity name) to retrieve additional context. "
                    "Otherwise, identify the single most critical missing piece of information and write a precise search query to find it.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What key facts from the first-hop passages (step1) are relevant to the claim?\n"
                    "2. What key facts from the second-hop passages (step4) are relevant?\n"
                    "3. What key facts from the third-hop passages (step8) are relevant?\n"
                    "4. What is the unified summary of all evidence?\n"
                    "5. Is the evidence sufficient to verify the claim? If not, what is missing?\n"
                    "6. What should be the search query: if insufficient, the missing fact; if sufficient, the main subject of the claim?"
                ),
                "example_reasoning": (
                    "Case 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop passages: [1] Eiffel Tower | Construction began in January 1887.\n"
                    "Second-hop passages: [1] Eiffel Tower | The construction was completed on March 31, 1889.\n"
                    "Third-hop passages: [1] Eiffel Tower | The Eiffel Tower was inaugurated on March 31, 1889.\n"
                    "Unified summary: Construction of the Eiffel Tower began in January 1887 and was completed on March 31, 1889.\n"
                    "Analysis: The claim is false because it was completed in 1889, not 1887. However, to ensure completeness, we retrieve more context on the Eiffel Tower.\n"
                    "Eiffel Tower\n\n"
                    "Case 2:\n"
                    "Claim: 'The Eiffel Tower is 300 meters tall.'\n"
                    "First-hop passages: [1] Eiffel Tower | The height of the Eiffel Tower is 300 meters without antennas.\n"
                    "Second-hop passages: [1] Eiffel Tower | The standard height measurement for the Eiffel Tower does not include the antennas.\n"
                    "Third-hop passages: [1] Eiffel Tower | Antennas add 24 meters to the total height.\n"
                    "Unified summary: The standard height of the Eiffel Tower is 300 meters (without antennas).\n"
                    "Analysis: The claim is true under the standard measurement. We retrieve more context on the Eiffel Tower.\n"
                    "Eiffel Tower"
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