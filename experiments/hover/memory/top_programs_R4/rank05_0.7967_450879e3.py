def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim. For multi-hop claims, at each hop generate multiple complementary search queries to maximize evidence diversity. Ensure queries within the same hop are non-redundant and cover distinct aspects.",
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
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the primary missing evidence after first hop and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine the primary specific fact missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical missing fact from the first-hop evidence? "
                    "Which entity or relationship is essential for verification but unconfirmed?"
                ),
                "example_reasoning": (
                    "The claim states 'X'. The first-hop passages mention Y but do not confirm Z, which is the primary fact required for verification. "
                    "Therefore, the missing fact is about Z. Query: 'Z'"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate complementary second-hop query",
                "step_type": "llm",
                "aim": "Identify a complementary missing evidence after first hop (different from the first query) and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop retrieved passages and the first query generated (which was '[first query]'), determine a different specific fact that is missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing that is not covered by the first query? "
                    "Which entities or relationships need further exploration that the first query did not address?"
                ),
                "example_reasoning": (
                    "The claim states 'X'. The first-hop passages mention Y but do not confirm Z or W. The first query was 'Z'. "
                    "Now, we need evidence about W. Query: 'W'"
                ),
                "dependencies": [1, 2],
            },
            {
                "number": 4,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Retrieve complementary second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing evidence after two hops (with two retrievals in hop2) and generate a precise search query for the third hop.",
                "stage_action": (
                    "Based on all evidence from first hop and both second-hop retrievals, determine the final piece of evidence needed to verify the claim. "
                    "This is the last opportunity to retrieve evidence. Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "First, summarize the key evidence gathered so far from all prior retrievals. Then, identify the single most critical missing fact that is still required to verify the claim. What is the last missing piece of evidence?"
                ),
                "example_reasoning": (
                    "So far, we have evidence about A, B, and C from the first and second hops. The claim requires also evidence about D. This is the last chance to find evidence for D. Query: 'D'"
                ),
                "dependencies": [1, 4, 5],
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