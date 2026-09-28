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
        "Missing information: Where was the Eiffel Tower originally intended to be built? Also, is there evidence of a connection to Barcelona?\n"
        "Output: 'Eiffel Tower original intended location | Eiffel Tower Barcelona connection'"
    )

    example_reasoning_step6 = (
        "Example:\n"
        "Claim: 'The Eiffel Tower was originally intended to be built in Barcelona.'\n"
        "First-hop summary: 'The Eiffel Tower is in Paris.'\n"
        "Second-hop summary: 'Some sources mention Barcelona, but it is unclear.'\n"
        "Missing information: What is the definitive evidence about the original intended location?\n"
        "Query: 'Eiffel Tower original intended location definitive source'"
    )

    example_reasoning_step9 = (
        "Example 1 (sufficient evidence):\n"
        "First-hop summary: 'The Eiffel Tower was built in Paris.'\n"
        "Second-hop summary: 'Historical records show no connection to Barcelona.'\n"
        "Third-hop summary: 'All design documents specify Paris as the location.'\n"
        "Analysis: The evidence is sufficient to confirm the claim is false.\n"
        "Output: NO_ADDITIONAL_EVIDENCE_NEEDED\n\n"
        "Example 2 (insufficient evidence):\n"
        "First-hop summary: 'The Eiffel Tower was built in Paris.'\n"
        "Second-hop summary: 'There is a rumor it was intended for Barcelona.'\n"
        "Third-hop summary: 'A rejected proposal for Barcelona exists but source is unclear.'\n"
        "Analysis: We need to verify the rejected proposal source.\n"
        "Output: 'Eiffel Tower rejected proposal Barcelona primary source'"
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
            # Step 3: Generate second-hop query (dual queries)
            {
                "number": 3,
                "title": "Generate dual second-hop queries",
                "step_type": "llm",
                "aim": "Identify two distinct missing evidence aspects and generate search queries.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Identify two distinct aspects of the missing evidence "
                    "and write two concise search queries, one for each aspect. "
                    "Output the two queries separated by ' | ', with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step3,
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (k=7)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
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
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary and the second-hop evidence summary, "
                    "determine what final piece of evidence is needed to fully verify the claim. "
                    "Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step6,
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (k=7)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence (NEW)
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            # Step 9: Gap analysis and fourth-hop query
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if current evidence is sufficient. If not, generate fourth-hop query.",
                "stage_action": (
                    "Review the first-hop evidence summary, the second-hop evidence summary, and the third-hop evidence summary. "
                    "Integrate these to form a comprehensive view. If the evidence is sufficient to verify the claim, "
                    "output 'NO_ADDITIONAL_EVIDENCE_NEEDED'. Otherwise, write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query or the exact string 'NO_ADDITIONAL_EVIDENCE_NEEDED', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": example_reasoning_step9,
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (k=7)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }