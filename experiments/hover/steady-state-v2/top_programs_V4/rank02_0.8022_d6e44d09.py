def entrypoint():
    system_prompt = (
        "You are an expert fact-checker. Your goal is to retrieve all evidence necessary to verify the claim. "
        "Be thorough: aim to find every relevant document. Break down the problem into hops, and at each hop, "
        "identify the precise missing information. Generate concise, effective search queries. "
        "After the third hop, check if the evidence is sufficient; if not, do a fourth hop."
    )

    example_reasoning_step3 = (
        "Example:\n"
        "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
        "First-hop summary: 'The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It was built from 1887 to 1889.'\n"
        "Missing information: Where was the Eiffel Tower originally intended to be built?\n"
        "Query: 'Eiffel Tower original intended location'"
    )

    example_reasoning_step7 = (
        "Example:\n"
        "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
        "Comprehensive summary after two hops: 'The Eiffel Tower was built in Paris. Some sources mention a connection to Barcelona, but it is unclear.'\n"
        "Missing information: What is the evidence about Barcelona?\n"
        "Query: 'Eiffel Tower Barcelona connection'"
    )

    example_reasoning_step9 = (
        "Example 1 (sufficient evidence):\n"
        "Comprehensive summary: 'The Eiffel Tower was built in Paris. Historical records confirm it was always intended for Paris.'\n"
        "Third-hop passages: [1] Eiffel Tower | Construction began in 1887 in Paris ... [2] ... no mention of Barcelona ...\n"
        "Analysis: The evidence is sufficient to confirm the claim is false.\n"
        "Output: NO_ADDITIONAL_EVIDENCE_NEEDED\n\n"
        "Example 2 (insufficient evidence):\n"
        "Comprehensive summary: 'The Eiffel Tower was built in Paris. There is a rumor it was intended for Barcelona, but the source is unclear.'\n"
        "Third-hop passages: [1] Eiffel Tower design | Designed by Gustave Eiffel for the 1889 exposition ... [2] ... mentions a rejected proposal for Barcelona?\n"
        "Analysis: We need to verify the rejected proposal for Barcelona.\n"
        "Output: 'Eiffel Tower rejected proposal Barcelona'"
    )

    return {
        "system_prompt": system_prompt,
        "steps": [
            # Step 1: First-hop retrieval (deep)
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step3,
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep)
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
            # Step 5: Summarize second-hop evidence (new)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            # Step 6: Integrate first and second hop evidence
            {
                "number": 6,
                "title": "Integrate first and second hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (from step 2) and the second-hop evidence summary (from step 5). "
                    "Produce a unified evidence summary covering all relevant facts found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2, 5],
            },
            # Step 7: Generate third-hop query
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the comprehensive evidence summary, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step7,
                "dependencies": [6],
            },
            # Step 8: Third-hop retrieval (deep)
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
            # Step 9: Gap analysis and fourth-hop query generation
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if current evidence is sufficient. If not, generate fourth-hop query.",
                "stage_action": (
                    "Review the comprehensive evidence summary (from step 6) and the third-hop passages (from step 8). "
                    "If the evidence is sufficient to verify the claim, output 'NO_ADDITIONAL_EVIDENCE_NEEDED'. "
                    "Otherwise, write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query or the exact string 'NO_ADDITIONAL_EVIDENCE_NEEDED', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step9,
                "dependencies": [6, 8],
            },
            # Step 10: Fourth-hop retrieval (deep)
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