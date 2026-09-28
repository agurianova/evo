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
                    "If fewer than three gaps exist, list only the actual gaps without inventing new ones."
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
                    "If the gap is already verified or not applicable, output an empty string. "
                    "Provide ONLY the search query text with no additional explanations."
                ),
                "reasoning_questions": (
                    "What key entity in this gap lacks evidence? "
                    "How can we phrase a query targeting this specific missing information?"
                ),
                "example_reasoning": (
                    "Gap: 'The location (Paris) where the treaty was signed.'\n"
                    "Treaty of Versailles signing location Paris"
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
                "aim": "Create complementary query for second gap using prior retrievals",
                "stage_action": (
                    "Based on the second gap from step 2 and the first retrieval results (step 4), "
                    "write a concise search query that targets remaining missing information without duplicating evidence. "
                    "If the gap is already verified or not applicable, output an empty string. "
                    "Provide ONLY the search query text with no additional explanations."
                ),
                "reasoning_questions": (
                    "What evidence is still missing after first retrieval? "
                    "How can we adjust the query to avoid overlap with step 4 results?"
                ),
                "example_reasoning": (
                    "Gap: 'The exact signing date (June 28) in 1919.'\n"
                    "First retrieval: Confirmed Paris location but no date.\n"
                    "Treaty of Versailles signing date June 28 1919"
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
                "aim": "Create query for third gap using all prior evidence",
                "stage_action": (
                    "Based on the third gap from step 2 and all prior retrieval results (steps 4 and 6), "
                    "write a concise search query targeting remaining missing information without duplication. "
                    "If no third gap exists or it's already verified, output an empty string. "
                    "Provide ONLY the search query text with no additional explanations."
                ),
                "reasoning_questions": (
                    "What critical information remains missing after two retrievals? "
                    "How can we craft a query that avoids overlapping with existing evidence?"
                ),
                "example_reasoning": (
                    "Gap: 'Official documentation confirming the signatories.'\n"
                    "First retrieval: Confirmed location and date but not signatories.\n"
                    "Treaty of Versailles signatory countries official document"
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
                "title": "Synthesize evidence and generate final query",
                "step_type": "llm",
                "aim": "Integrate all evidence and create third-hop query for critical gap",
                "stage_action": (
                    "Combine initial evidence summary (step 2) with all second-hop passages (steps 4, 6, 8). "
                    "Cross-validate evidence for consistency and identify contradictions. "
                    "Then, explicitly state the single most critical missing piece of information required for verification. "
                    "Based on this gap, write a precise search query. "
                    "If all evidence is verified, output an empty string. "
                    "Provide ONLY the search query text with no additional explanations."
                ),
                "reasoning_questions": (
                    "What key aspect remains unverified after combining all evidence? "
                    "Which gap is most essential to close for conclusive verification?"
                ),
                "example_reasoning": (
                    "Combined evidence: Source A states signing occurred June 28, but Source B claims July 1.\n"
                    "Treaty of Versailles primary source signing date"
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
