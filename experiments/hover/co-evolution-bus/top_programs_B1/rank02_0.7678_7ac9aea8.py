def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker specializing in multi-hop evidence retrieval. Summarizers extract ONLY claim-relevant facts; query generators output ONLY the search query string. Prioritize precision and conciseness.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key entities and factual claims from retrieved passages relevant to the claim.",
                "stage_action": (
                    "List bullet points of key entities (people, places, dates) and verifiable facts. "
                    "Extract ONLY facts directly relevant to verifying the claim. Exclude opinions, irrelevant details, and potential noise."
                ),
                "reasoning_questions": (
                    "1. What are the main entities mentioned?\n"
                    "2. What specific facts (dates, numbers, events) are stated?\n"
                    "3. How do these facts directly relate to the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was completed in 1887.'\n"
                    "Passages:\n"
                    "[1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\n"
                    "Key entities: Eiffel Tower\n"
                    "Facts: Construction began in 1887; completed in 1889.\n"
                    "Relation: Claim states completion in 1887, but passage says 1889."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing link to verify claim and generate focused search query.",
                "stage_action": (
                    "Based on the bullet-point summary, determine what specific information is missing. "
                    "Write a search query targeting the second gold document. Include specific entities/dates from evidence. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": (
                    "1. What key fact from the claim is unsupported by first-hop evidence?\n"
                    "2. What specific entity or event should we search for next?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was completed in 1887.'\n"
                    "Summary:\n"
                    "- Entities: Eiffel Tower\n"
                    "- Facts: Construction began in 1887; completed in 1889.\n"
                    "Eiffel Tower completion year"
                ),
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into unified verification-focused summary.",
                "stage_action": (
                    "Integrate first-hop summary with second-hop passages. List bullet points of all key entities "
                    "and verifiable facts. Exclude redundant information. Then, state the single missing fact "
                    "that is essential to verify the claim in the format: 'Missing fact: [fact]'"
                ),
                "reasoning_questions": (
                    "1. What new entities/facts appear in second-hop passages?\n"
                    "2. How do these connect to first-hop evidence and claim?\n"
                    "3. What single fact is still missing to confirm/refute the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Aspirin is derived from willow bark.'\n"
                    "First-hop summary:\n"
                    "- Entities: Aspirin, willow bark\n"
                    "- Facts: Willow bark contains salicin, a precursor to salicylic acid.\n"
                    "Second-hop passages:\n"
                    "[1] Acetylsalicylic acid | Synthesized from salicylic acid and acetic anhydride.\n"
                    "Unified summary:\n"
                    "- Entities: Aspirin, willow bark, salicylic acid\n"
                    "- Facts: Willow bark → salicin → salicylic acid; salicylic acid + acetic anhydride → acetylsalicylic acid.\n"
                    "Missing fact: Chemical process converting salicylic acid to acetylsalicylic acid"
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate precise query for the single missing fact using evidence from prior steps.",
                "stage_action": (
                    "Using the 'Missing fact' statement from previous step, generate a highly specific search query. "
                    "Include key entities, conditions, and technical terms from evidence. "
                    "Output ONLY the query string with no additional text, not even 'Query: '."
                ),
                "reasoning_questions": (
                    "1. What specific terms from the missing fact are most searchable?\n"
                    "2. Which technical terms/entities will best target the gold document?"
                ),
                "example_reasoning": (
                    "Claim: 'Aspirin is derived from willow bark.'\n"
                    "Unified summary:\n"
                    "- Entities: Aspirin, willow bark, salicylic acid\n"
                    "- Facts: Willow bark → salicin → salicylic acid; salicylic acid + acetic anhydride → acetylsalicylic acid.\n"
                    "Missing fact: Chemical process converting salicylic acid to acetylsalicylic acid\n"
                    "acetylsalicylic acid synthesis from salicylic acid"
                ),
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
