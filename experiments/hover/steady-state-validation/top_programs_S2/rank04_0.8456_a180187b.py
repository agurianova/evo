def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to maximize evidence recall by thoroughly exploring all relevant information. Always prioritize finding all supporting documents over speed. Focus on generating comprehensive queries that cover multiple angles when evidence is incomplete.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve initial passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Summarize initial evidence and identify critical gaps",
                "step_type": "llm",
                "aim": "Extract key facts and identify up to three critical non-redundant evidence gaps",
                "stage_action": (
                    "Read the retrieved passages and summarize key evidence relevant to the claim. "
                    "Then, explicitly list up to three distinct critical and non-redundant pieces of missing information necessary for verification. "
                    "Each gap must represent a different critical aspect directly required to verify the claim and not covered by current evidence. "
                    "If the claim is simple, you may list fewer than three gaps."
                ),
                "reasoning_questions": (
                    "What critical aspects of the claim remain unverified by current evidence? "
                    "How can we ensure gaps address distinct verification requirements?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in Paris on June 28, 1919.'\n"
                    "Evidence: Passages confirm the 1919 signing year but omit location and exact date.\n"
                    "Gaps:\n"
                    "1. The location (Paris) where the treaty was signed.\n"
                    "2. The exact signing date (June 28) in 1919."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Create search query for first evidence gap",
                "stage_action": (
                    "Based on the first gap from step 2, write a concise search query. "
                    "Provide ONLY the search query text with no additional explanations."
                ),
                "reasoning_questions": (
                    "What key entity in this gap lacks evidence? "
                    "How can we phrase a query targeting this specific missing information?"
                ),
                "example_reasoning": (
                    "Gap: 'The location (Paris) where the treaty was signed.'\n"
                    "Query: 'Treaty of Versailles signing location Paris'"
                ),
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve for first second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Create search query for second evidence gap, avoiding duplication",
                "stage_action": (
                    "Based on the second gap from step 2 and the first retrieval results (step 4), "
                    "write a concise search query that targets the missing information without duplicating evidence. "
                    "If the second gap is already verified by the initial evidence or step 4 results, output an empty string. "
                    "Provide ONLY the search query text or empty string with no additional explanations."
                ),
                "reasoning_questions": (
                    "What evidence is still missing for the second gap after reviewing step 4 results? "
                    "How can we adjust the query to avoid overlap with step 4 results?"
                ),
                "example_reasoning": (
                    "Gap: 'The exact signing date (June 28) in 1919.'\n"
                    "Step4 results: Confirmed Paris location but no date information.\n"
                    "Query: 'Treaty of Versailles signing date June 28 1919'\n"
                    "\n"
                    "OR if step4 had already provided the date:\n"
                    "Step4 results: Also mention June 28 signing date.\n"
                    "Output: (empty string)"
                ),
                "dependencies": [2, 4],
            },
            {
                "number": 6,
                "title": "Retrieve for second second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},
                },
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Generate third second-hop query",
                "step_type": "llm",
                "aim": "Create complementary query for third gap using available evidence",
                "stage_action": (
                    "Based on the third gap from step 2 (if any) and all available evidence (initial, step4, step6), "
                    "write a concise search query that targets the missing information without duplicating evidence. "
                    "If the third gap is already verified by any available evidence, output an empty string. "
                    "Provide ONLY the search query text or empty string with no additional explanations."
                ),
                "reasoning_questions": (
                    "What evidence is still missing for the third gap? "
                    "How can we phrase a query that avoids overlap with existing evidence?"
                ),
                "example_reasoning": (
                    "Gap: 'The reason for the signing location being Paris.'\n"
                    "Available evidence: Confirms Paris location and June 28 date, but no reason.\n"
                    "Query: 'Treaty of Versailles why signed in Paris'\n"
                    "\n"
                    "OR if the reason is found in step6:\n"
                    "Available evidence: ... mentions that Paris was chosen for historical reasons.\n"
                    "Output: (empty string)"
                ),
                "dependencies": [2, 4, 6],
            },
            {
                "number": 8,
                "title": "Retrieve for third second-hop query",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Synthesize evidence and generate critical gap query",
                "step_type": "llm",
                "aim": "Integrate all evidence and generate search query for the most critical remaining gap",
                "stage_action": (
                    "Combine the initial evidence summary (step2) with all second-hop passages (steps4,6,8). "
                    "Cross-validate evidence for consistency and identify contradictions. "
                    "If there is at least one critical piece of missing information required for verification, output ONLY the search query for the most critical missing piece. "
                    "If all evidence is verified, output an empty string."
                ),
                "reasoning_questions": (
                    "What key aspect remains unverified after combining all evidence? "
                    "Which gap is most essential to close for conclusive verification? "
                    "How can we formulate a precise query for this gap?"
                ),
                "example_reasoning": (
                    "Claim: 'The Treaty of Versailles was signed in Paris on June 28, 1919.'\n"
                    "Initial evidence: Confirms 1919 year.\n"
                    "Step4: Confirms Paris location.\n"
                    "Step6: States June 28 date but conflicts with another source (July 1).\n"
                    "Step8: No additional relevant evidence.\n"
                    "Critical gap: Official document confirming the exact date.\n"
                    "Query: 'Treaty of Versailles primary source signing date'"
                ),
                "dependencies": [2, 4, 6, 8],
            },
            {
                "number": 10,
                "title": "Retrieve final passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[8]"},
                },
                "dependencies": [9],
            },
        ],
    }
