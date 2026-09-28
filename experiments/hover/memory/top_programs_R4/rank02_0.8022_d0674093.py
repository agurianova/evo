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
                "title": "Generate first-hop2 query (branch 1)",
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
                    "The missing fact is about Z. Z"
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
                "title": "Generate second-hop2 query (branch 2)",
                "step_type": "llm",
                "aim": "Identify additional missing evidence after reviewing the first hop and the first branch of the second hop, and generate a second search query for the second hop, branch 2.",
                "stage_action": (
                    "Based on the first-hop passages and the first branch second-hop passages, determine if the first branch provided relevant evidence. "
                    "If not, generate a radically different query for an alternative evidence path. "
                    "If yes, identify gaps unaddressed by the first branch and generate a query for a different entity or relationship. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Did the first branch results address the initial gap? "
                    "If not, what alternative evidence path should be explored? "
                    "If yes, what gaps remain unaddressed by the first branch and which alternative entity or relationship might hold the evidence?"
                ),
                "example_reasoning": (
                    "The first-hop passages mention A. The first branch results are about X, which is unrelated to the claim. "
                    "Therefore, the first branch did not address the gap. Generate a radically different query for an alternative evidence path. "
                    "The missing fact is likely about C. C"
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
                "title": "Generate hop3 query (final hop)",
                "step_type": "llm",
                "aim": "Identify the final missing evidence after reviewing all evidence from first hop and both branches of second hop, and generate a precise search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine the most critical missing piece of evidence needed to verify the claim. "
                    "If multiple gaps exist, prioritize the one that is most essential. "
                    "Write a concise search query to find that evidence. This is the final opportunity to retrieve evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical missing fact? "
                    "Has all other evidence been gathered? "
                    "Which specific detail is still absent and most vital to verification?"
                ),
                "example_reasoning": (
                    "The evidence so far covers A, B, and C but does not confirm D or E. "
                    "D is more critical because it directly verifies the claim's main assertion. "
                    "The most critical missing fact is D. D"
                ),
                "dependencies": [1, 3, 5],
            },
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
        ],
    }