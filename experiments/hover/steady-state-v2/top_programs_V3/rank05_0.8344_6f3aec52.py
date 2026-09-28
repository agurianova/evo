def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier specializing in multi-hop claim verification. Your goal is to maximize retrieval coverage. When generating search queries, prioritize recall over precision to capture as many potentially relevant documents as possible. STRICTLY OUTPUT THE QUERY AND NOTHING ELSE. When synthesizing evidence, prioritize recall for gap listing: list EVERY missing evidence requirement, even if uncertain, and then focus on precision to ensure gaps are distinct and orthogonal.",
        "steps": [
            # Step 1: First-hop retrieval with deep search (k=10) to maximize initial recall
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
            # Step 2: Generate single second-hop query with recall focus
            {
                "number": 2,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence and generate a broad search query.",
                "stage_action": (
                    "Analyze the raw passages from step1 to determine the single most critical piece of evidence missing for claim verification. "
                    "Write a broad search query targeting this gap to maximize recall. STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "What is the primary evidence gap? Which terms would best maximize recall for this missing information?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Passages: [1] Eiffel Tower | Built in Paris from 1887 to 1889. [2] Gustave Eiffel | French engineer.\n"
                    "Missing gap: Source of construction iron.\n"
                    "Query: 'Eiffel Tower iron source Lorraine region construction materials'"
                ),
                "dependencies": [1],
            },
            # Step 3: Second-hop retrieval with deep search (k=10)
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
            # Step 4: Early evidence synthesis with recall-focused gap identification
            {
                "number": 4,
                "title": "Synthesize evidence and identify gaps",
                "step_type": "llm",
                "aim": "Produce structured summary listing EVERY missing evidence requirement with orthogonal gaps.",
                "stage_action": (
                    "Integrate passages from step1 (first hop) and step3 (second hop). Remove duplicate information. "
                    "Output in EXACT format:\n"
                    "Verified facts: [comma-separated list]\n"
                    "Missing evidence:\n"
                    "  Gap 1: [description]\n"
                    "  Gap 2: [description]\n"
                    "  Gap 3: [description]\n"
                    "(List EVERY missing evidence requirement; ensure gaps are orthogonal and cover distinct aspects. Prioritize recall: list all possible gaps.)"
                ),
                "reasoning_questions": "What has been confirmed? What EVERY piece of evidence is still missing? Why are these gaps distinct and non-overlapping?",
                "example_reasoning": (
                    "Example:\n"
                    "Claim: 'The Eiffel Tower was constructed using iron from the Lorraine region.'\n"
                    "Verified facts: Built 1887-1889, Gustave Eiffel engineer, Early skyscrapers used wrought iron\n"
                    "Missing evidence:\n"
                    "  Gap 1: Direct evidence of iron sourcing from Lorraine region\n"
                    "  Gap 2: Documentation of iron shipment logistics from Lorraine to Paris\n"
                    "  Gap 3: Contract records specifying Lorraine as iron source"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Generate third-hop query for Gap 1
            {
                "number": 5,
                "title": "Generate first third-hop query",
                "step_type": "llm",
                "aim": "Create broad query targeting the first evidence gap.",
                "stage_action": (
                    "Based on the 'Gap 1' description in step4's output, write a broad search query to maximize recall for this gap. "
                    "STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "What specific terms would best maximize recall for Gap 1?",
                "example_reasoning": (
                    "Example:\n"
                    "Gap 1: Direct evidence of iron sourcing from Lorraine region\n"
                    "Query: 'Eiffel Tower construction iron supplier Lorraine region primary source'"
                ),
                "dependencies": [4],
            },
            # Step 6: First third-hop retrieval
            {
                "number": 6,
                "title": "Retrieve first third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [5],
            },
            # Step 7: Generate third-hop query for Gap 2 (avoiding redundancy)
            {
                "number": 7,
                "title": "Generate second third-hop query",
                "step_type": "llm",
                "aim": "Create distinct broad query targeting the second evidence gap.",
                "stage_action": (
                    "Based on the 'Gap 2' description in step4's output and the first third-hop results (step6), "
                    "write a DISTINCT broad search query for Gap 2 that avoids overlap with step5's query. "
                    "STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "How is Gap 2 different from Gap 1? What alternative terms would maximize recall without overlapping?",
                "example_reasoning": (
                    "Example:\n"
                    "Gap 2: Documentation of iron shipment logistics from Lorraine to Paris\n"
                    "First third-hop passages: [1] Iron suppliers | Lorraine region was a major iron producer.\n"
                    "New query: 'Eiffel Tower construction records iron transportation routes Lorraine Paris'"
                ),
                "dependencies": [4, 6],
            },
            # Step 8: Second third-hop retrieval
            {
                "number": 8,
                "title": "Retrieve second third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            # Step 9: Generate third-hop query for Gap 3 (avoiding all prior redundancy)
            {
                "number": 9,
                "title": "Generate third third-hop query",
                "step_type": "llm",
                "aim": "Create distinct broad query targeting the third evidence gap.",
                "stage_action": (
                    "Based on the 'Gap 3' description in step4's output and the first two third-hop results (step6 and step8), "
                    "write a DISTINCT broad search query for Gap 3 that avoids overlap with step5 and step7's queries. "
                    "STRICTLY OUTPUT THE QUERY AND NOTHING ELSE."
                ),
                "reasoning_questions": "How is Gap 3 different from previous gaps? What unique terms would maximize recall without overlapping prior queries?",
                "example_reasoning": (
                    "Example:\n"
                    "Gap 3: Contract records specifying Lorraine as iron source\n"
                    "First third-hop passages: [1] Iron suppliers | Lorraine region was a major iron producer.\n"
                    "Second third-hop passages: [1] Transportation logistics | Iron was shipped via rail from Lorraine.\n"
                    "New query: 'Eiffel Tower construction contracts Lorraine iron supplier documentation'"
                ),
                "dependencies": [4, 6, 8],
            },
            # Step 10: Third third-hop retrieval
            {
                "number": 10,
                "title": "Retrieve third third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }