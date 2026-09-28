def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim. For multi-hop claims, you may generate multiple search queries per hop to explore different evidence paths. Always prioritize finding missing evidence that directly verifies or refute the claim.",
        "steps": [
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
            {
                "number": 2,
                "title": "Generate first-hop query (branch 1)",
                "step_type": "llm",
                "aim": "Identify the first critical missing evidence after the first hop and generate a precise search query for the second hop, branch 1.",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine the most important specific fact missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical missing fact from the first-hop evidence? "
                    "Which entity or relationship should be explored first?"
                ),
                "example_reasoning": (
                    "The claim states 'X'. The first-hop passages mention Y but do not confirm Z, which is essential. "
                    "The missing fact is about Z. 'Z'"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve second-hop passages (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate second-hop query (branch 2)",
                "step_type": "llm",
                "aim": "Identify additional missing evidence after reviewing the first hop and the first branch of the second hop, and generate a second search query for the second hop, branch 2.",
                "stage_action": (
                    "Based on the first-hop passages and the first branch second-hop passages, determine what specific fact is still missing to verify the claim. "
                    "Write a concise search query focused on a different entity or relationship than branch 1 to find that evidence. "
                    "If the first branch results lack relevant evidence, generate a radically different query. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What gaps remain after seeing the first branch results? "
                    "Which alternative entities or relationships might hold the missing evidence? "
                    "How is this query different from the first branch query?"
                ),
                "example_reasoning": (
                    "The first hop and first branch cover A and B but do not address C. "
                    "The missing fact is about C. 'C'"
                ),
                "dependencies": [1, 3],
            },
            {
                "number": 5,
                "title": "Retrieve second-hop passages (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate final hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing evidence after reviewing all evidence from first hop and both branches of second hop, and generate a precise search query for the final hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine the most critical piece of evidence still needed to verify the claim. "
                    "Write a concise search query to find that evidence. This is the final opportunity to retrieve evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical missing fact among remaining gaps? "
                    "Which specific detail would most strongly verify or refute the claim?"
                ),
                "example_reasoning": (
                    "All evidence so far supports the claim except for key detail about D. "
                    "Among remaining gaps, the most critical is D. 'D'"
                ),
                "dependencies": [1, 3, 5],
            },
            {
                "number": 7,
                "title": "Retrieve final-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }