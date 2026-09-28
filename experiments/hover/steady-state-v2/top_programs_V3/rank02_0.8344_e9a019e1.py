def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier specializing in multi-hop claim verification. Your goal is to maximize retrieval coverage. When generating search queries, prioritize recall over precision to capture as many potentially relevant documents as possible. STRICTLY OUTPUT THE QUERY AND NOTHING ELSE. When synthesizing evidence, focus on precision by identifying distinct, orthogonal evidence gaps that are not covered by any retrieved passages.",
        "steps": [
            # Step 1: First-hop retrieval with standard search (k=7) to reduce noise
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
            # Step 2: Generate first second-hop query
            {
                "number": 2,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence and generate a focused search query.",
                "stage_action": (
                    "Analyze the raw passages from step1 to determine the single most critical piece of evidence missing for claim verification. "
                    "Write a concise search query targeting this gap. STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "What is the primary evidence gap? Which specific terms would best capture this missing information?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Passages: [1] Eiffel Tower | Built in Paris from 1887 to 1889. [2] Gustave Eiffel | French engineer.\n"
                    "Missing gap: Source of construction iron.\n"
                    "Query: 'Eiffel Tower iron source Lorraine region'"
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
            # Step 4: Generate second second-hop query (using first second-hop results to avoid redundancy)
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a different critical evidence gap using first second-hop results and generate a distinct query.",
                "stage_action": (
                    "Analyze the raw passages from step1 and the first second-hop results (step3) to identify a SECOND critical evidence gap "
                    "that is distinct from the first. Write a concise search query targeting this new gap. "
                    "STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "What gap remains unaddressed by the first query? How can we phrase this differently using synonyms or alternative perspectives?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Passages: [1] Eiffel Tower | Built in Paris from 1887 to 1889. [2] Gustave Eiffel | French engineer.\n"
                    "First second-hop passages: [1] Iron in construction | Early skyscrapers used wrought iron.\n"
                    "New gap: Documentation of iron shipment logistics.\n"
                    "Query: 'Eiffel Tower construction records iron transportation Lorraine'"
                ),
                "dependencies": [1, 3],  # Added dependency on step3 (first second-hop results)
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
            # Step 6: Structured evidence synthesis with comprehensive gap identification
            {
                "number": 6,
                "title": "Synthesize evidence and identify gaps",
                "step_type": "llm",
                "aim": "Produce structured summary listing EVERY missing evidence requirement with orthogonal gaps.",
                "stage_action": (
                    "Integrate passages from step1 (first hop), step3 (first second-hop), and step5 (second second-hop). "
                    "Output in EXACT format:\n"
                    "Verified facts: [comma-separated list]\n"
                    "Missing evidence:\n"
                    "  Gap 1: [description]\n"
                    "  Gap 2: [description]\n"
                    "  ... (list EVERY missing evidence requirement; ensure gaps are orthogonal and cover distinct aspects)"
                ),
                "reasoning_questions": "What has been confirmed? What EVERY piece of evidence is still missing? Why are these gaps distinct and non-overlapping?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Verified facts: Built 1887-1889, Gustave Eiffel engineer, Early skyscrapers used wrought iron\n"
                    "Missing evidence:\n"
                    "  Gap 1: Direct evidence of iron sourcing from Lorraine\n"
                    "  Gap 2: Documentation of iron shipment logistics from Lorraine to Paris\n"
                    "  Gap 3: Contract records specifying Lorraine as source"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Generate first third-hop query for Gap 1
            {
                "number": 7,
                "title": "Generate first third-hop query",
                "step_type": "llm",
                "aim": "Create query targeting the first identified evidence gap.",
                "stage_action": (
                    "Based on the 'Gap 1' description in step6's output, write a concise search query to find this evidence. "
                    "STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "What specific terms would best capture Gap 1? How can we maximize recall for this gap?",
                "example_reasoning": (
                    "Example:\n"
                    "Gap 1: Direct evidence of iron sourcing from Lorraine\n"
                    "Query: 'Eiffel Tower construction iron supplier Lorraine region'"
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
            # Step 9: Generate second third-hop query for Gap 2 (using first third-hop results to avoid redundancy)
            {
                "number": 9,
                "title": "Generate second third-hop query",
                "step_type": "llm",
                "aim": "Create distinct query targeting the second evidence gap using first third-hop results.",
                "stage_action": (
                    "Based on the 'Gap 2' description in step6's output and the first third-hop results (step8), "
                    "write a DISTINCT search query for Gap 2 that avoids overlap with step7's query. "
                    "STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "How is Gap 2 different from Gap 1? What alternative terms would capture this gap without overlapping with step7's query?",
                "example_reasoning": (
                    "Example:\n"
                    "Gap 2: Documentation of iron shipment logistics from Lorraine to Paris\n"
                    "First third-hop passages: [1] Iron suppliers | Lorraine region was a major iron producer.\n"
                    "New query: 'Eiffel Tower construction records iron transportation Lorraine Paris'"
                ),
                "dependencies": [6, 8],  # Added dependency on step8 (first third-hop results)
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