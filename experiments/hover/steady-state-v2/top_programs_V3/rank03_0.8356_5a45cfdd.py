def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier specializing in multi-hop claim verification. Your goal is to maximize retrieval coverage. For query generation steps, prioritize recall over precision; for synthesis steps, focus on precision.",
        "steps": [
            # Step 1: First-hop retrieval with increased recall (k=10)
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
            # Step 2: Generate first second-hop query with synonym expansion
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence and generate a focused search query.",
                "stage_action": (
                    "Analyze the raw passages from step1 to determine the single most critical piece of evidence missing for claim verification. "
                    "Write a concise search query targeting this gap, including 2-3 key synonyms for the main entities to maximize recall. "
                    "STRICTLY OUTPUT THE SEARCH QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "What is the primary evidence gap? Which specific terms would best capture this missing information?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Passages: [1] Eiffel Tower | Built in Paris from 1887 to 1889. [2] Gustave Eiffel | French engineer.\n"
                    "Missing gap: Source of construction iron.\n"
                    "Query: 'Eiffel Tower iron source Lorraine region steel metalworks'"
                ),
                "dependencies": [1],
            },
            # Step 3: First second-hop retrieval (deep search)
            {
                "number": 3,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            # Step 4: Generate second second-hop query with gap existence check and distinctness
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different critical evidence gap using first-hop and first second-hop results.",
                "stage_action": (
                    "Analyze the raw passages from step1, the first query (step2), and the first second-hop results (step3) to identify a SECOND critical evidence gap "
                    "that is distinct from the first and not addressed by step3. If such a gap exists, write a concise search query targeting this new gap "
                    "using synonyms and alternative phrasings to avoid term overlap with the first query (step2). If no second gap exists, output the string 'NO_QUERY'. "
                    "STRICTLY OUTPUT THE SEARCH QUERY OR 'NO_QUERY' AND NOTHING ELSE."
                ),
                "reasoning_questions": "What gap remains unaddressed by the first query and step3 results? How can we phrase this differently using synonyms?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Passages (step1): [1] Eiffel Tower | Built in Paris from 1887 to 1889. [2] Gustave Eiffel | French engineer.\n"
                    "First query: 'Eiffel Tower iron source Lorraine region'\n"
                    "Step3 results: [1] Lorraine region | Known for iron ore deposits. [2] Eiffel Tower construction | Used puddled iron.\n"
                    "New gap: Documentation of iron shipment logistics.\n"
                    "Query: 'Eiffel Tower construction records iron transportation Lorraine Paris freight'\n\n"
                    "OR if no second gap: 'NO_QUERY'"
                ),
                "dependencies": [1, 2, 3],
            },
            # Step 5: Second second-hop retrieval (deep search)
            {
                "number": 5,
                "title": "Retrieve second second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            # Step 6: Comprehensive evidence synthesis with gap orthogonality
            {
                "number": 6,
                "title": "Synthesize evidence and identify gaps",
                "step_type": "llm",
                "aim": "Produce structured summary with all missing evidence requirements.",
                "stage_action": (
                    "Integrate passages from step1, step3, and step5. List EVERY piece of evidence required by the claim that is not supported. "
                    "Ensure gaps are orthogonal and cover distinct aspects. Output in EXACT format:\n"
                    "Verified facts: [comma-separated list]\n"
                    "Missing evidence:\n"
                    "  Gap 1: [description]\n"
                    "  Gap 2: [description]\n"
                    "  [Gap 3: ... if applicable]"
                ),
                "reasoning_questions": "What has been confirmed? List every missing evidence requirement. Why are these gaps distinct and orthogonal?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Verified facts: Built 1887-1889, Gustave Eiffel engineer, Lorraine iron ore deposits\n"
                    "Missing evidence:\n"
                    "  Gap 1: Direct evidence of iron sourcing from Lorraine for Eiffel Tower\n"
                    "  Gap 2: Documentation of iron shipment logistics from Lorraine to Paris\n"
                    "  Gap 3: Quantity of iron transported from Lorraine"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Generate first third-hop query with synonym expansion
            {
                "number": 7,
                "title": "Generate first third-hop query",
                "step_type": "llm",
                "aim": "Create query targeting the first identified evidence gap.",
                "stage_action": (
                    "Based on the 'Gap 1' description in step6's output, write a concise search query to find this evidence, "
                    "including 2-3 key synonyms for the main entities to maximize recall. "
                    "STRICTLY OUTPUT THE SEARCH QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "What specific terms would best capture Gap 1? How can we maximize recall for this gap?",
                "example_reasoning": (
                    "Example:\n"
                    "Gap 1: Direct evidence of iron sourcing from Lorraine\n"
                    "Query: 'Eiffel Tower construction iron supplier Lorraine region documentation proof'"
                ),
                "dependencies": [6],
            },
            # Step 8: First third-hop retrieval (deep search)
            {
                "number": 8,
                "title": "Retrieve first third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Generate second third-hop query with gap existence check and distinctness
            {
                "number": 9,
                "title": "Generate second third-hop query",
                "step_type": "llm",
                "aim": "Create distinct query using first third-hop results.",
                "stage_action": (
                    "If step6 output contains a 'Gap 2', then based on the 'Gap 2' description, the first third-hop query (step7), and the first third-hop results (step8), "
                    "write a search query for Gap 2 using synonyms and alternative phrasings to avoid term overlap with step7. "
                    "If step6 output does not contain 'Gap 2', output the string 'NO_QUERY'. "
                    "STRICTLY OUTPUT THE SEARCH QUERY OR 'NO_QUERY' AND NOTHING ELSE."
                ),
                "reasoning_questions": "How is Gap 2 different from Gap 1? What alternative terms avoid overlap with step7/step8?",
                "example_reasoning": (
                    "Example:\n"
                    "Gap 2: Documentation of iron shipment logistics from Lorraine to Paris\n"
                    "First query: 'Eiffel Tower construction iron supplier Lorraine region'\n"
                    "Step8 results: [1] Construction records | Iron sourced from Lorraine mines.\n"
                    "New query: 'Eiffel Tower construction logistics iron transport Lorraine Paris freight'\n\n"
                    "OR if no Gap 2: 'NO_QUERY'"
                ),
                "dependencies": [6, 7, 8],
            },
            # Step 10: Second third-hop retrieval (deep search)
            {
                "number": 10,
                "title": "Retrieve second third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }