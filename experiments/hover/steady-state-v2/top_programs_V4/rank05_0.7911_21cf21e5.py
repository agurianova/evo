def entrypoint():
    system_prompt = (
        "You are an expert fact-checker. Your goal is to retrieve all evidence necessary to verify the claim. "
        "Be thorough: aim to find every relevant document. Break down the problem into hops, and at each hop, "
        "identify precise missing information. Generate concise, effective search queries, and consider "
        "multiple distinct queries to explore different evidence paths. After the third hop, "
        "check if evidence is sufficient; if not, prepare a fourth-hop query."
    )

    example_reasoning_step3 = (
        "Example:\n"
        "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
        "First-hop summary: 'The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It was built from 1887 to 1889.'\n"
        "Missing information: Where was the Eiffel Tower originally intended to be built?\n"
        "Query: 'Eiffel Tower original intended location'"
    )

    example_reasoning_step4 = (
        "Example:\n"
        "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
        "First-hop summary: 'The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It was built from 1887 to 1889.'\n"
        "Missing information: What is the connection between the Eiffel Tower and Barcelona?\n"
        "Query: 'Eiffel Tower Barcelona connection'"
    )

    example_reasoning_step7 = (
        "Example:\n"
        "First-hop summary: 'The Eiffel Tower was built in Paris between 1887-1889.'\n"
        "Second-hop passages for query1: [1] Design history | Initially proposed for Barcelona but rejected ...\n"
        "Second-hop passages for query2: [1] Barcelona records | City council minutes mention Eiffel proposal ...\n"
        "Comprehensive summary: 'The Eiffel Tower was built in Paris. Historical records confirm the design was initially proposed to Barcelona but rejected, so it was constructed in Paris.'"
    )

    example_reasoning_step8 = (
        "Example:\n"
        "Comprehensive summary: 'The Eiffel Tower was built in Paris. Historical records confirm the design was initially proposed to Barcelona but rejected.'\n"
        "Missing information: What was the reason for Barcelona's rejection?\n"
        "Query: 'Eiffel Tower Barcelona rejection reason'"
    )

    example_reasoning_step10 = (
        "Example 1 (sufficient evidence):\n"
        "Comprehensive summary: 'The Eiffel Tower was built in Paris. Historical records confirm it was always intended for Paris.'\n"
        "Third-hop summary: 'No evidence found of any connection to Barcelona.'\n"
        "Analysis: The evidence is sufficient to confirm the claim is false.\n"
        "Output: NO_ADDITIONAL_EVIDENCE_NEEDED\n\n"
        "Example 2 (insufficient evidence):\n"
        "Comprehensive summary: 'The Eiffel Tower was built in Paris. There is a rumor it was intended for Barcelona, but the source is unclear.'\n"
        "Third-hop summary: 'One passage mentions a rejected proposal for Barcelona, but no details.'\n"
        "Analysis: We need to verify the rejected proposal details.\n"
        "Output: 'Eiffel Tower Barcelona rejection details'"
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
            # Step 3: Generate first second-hop query
            {
                "number": 3,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify one missing information path and generate a search query.",
                "stage_action": (
                    "Based on the first-hop summary, determine one specific piece of missing evidence "
                    "needed to verify the claim. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step3,
                "dependencies": [2],
            },
            # Step 4: Generate second second-hop query
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different missing information path and generate an alternative query.",
                "stage_action": (
                    "Based on the first-hop summary, determine a distinct piece of missing evidence "
                    "not covered by the first query. Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step4,
                "dependencies": [2],
            },
            # Step 5: First second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve passages for first second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},  # Step 3 output
                },
                "dependencies": [3],
            },
            # Step 6: Second second-hop retrieval
            {
                "number": 6,
                "title": "Retrieve passages for second second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},  # Step 4 output
                },
                "dependencies": [4],
            },
            # Step 7: Integrate evidence into comprehensive summary
            {
                "number": 7,
                "title": "Integrate evidence into comprehensive summary",
                "step_type": "llm",
                "aim": "Combine all evidence into a unified summary covering all hops.",
                "stage_action": (
                    "Read the first-hop summary (from step 2), and the second-hop passages "
                    "(from steps 5 and 6). Identify all relevant facts for verifying the claim. "
                    "Produce a single comprehensive evidence summary."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step7,
                "dependencies": [2, 5, 6],
            },
            # Step 8: Generate third-hop query
            {
                "number": 8,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a precise third-hop query.",
                "stage_action": (
                    "Based on the comprehensive evidence summary, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step8,
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[7]"},  # Step 8 output
                },
                "dependencies": [8],
            },
            # Step 10: Third-hop summary and gap analysis
            {
                "number": 10,
                "title": "Summarize third hop and gap analysis",
                "step_type": "llm",
                "aim": "Summarize third-hop evidence and determine if fourth hop is needed.",
                "stage_action": (
                    "Read the third-hop passages (from step 9) and summarize the key evidence. "
                    "Then, review the comprehensive evidence summary (from step 7) and this summary. "
                    "If the evidence is sufficient to verify the claim, output 'NO_ADDITIONAL_EVIDENCE_NEEDED'. "
                    "Otherwise, write a concise search query for the missing evidence.\n"
                    "Provide ONLY the exact string 'NO_ADDITIONAL_EVIDENCE_NEEDED' or the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step10,
                "dependencies": [7, 9],
            },
        ],
    }