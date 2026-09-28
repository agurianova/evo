def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim. For each hop, generate a precise search query based on the evidence gathered so far to maximize coverage of supporting documents.",
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
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the missing evidence after first hop and generate a precise search query for the second hop.",
                "stage_action": (
                    "First, summarize the key evidence from the first-hop retrieved passages. "
                    "Then, determine the specific fact missing to verify the claim that has not been confirmed by the evidence. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key evidence is present in the first-hop passages? "
                    "What specific fact is missing to verify the claim?"
                ),
                "example_reasoning": (
                    "The first-hop passages mention that [entity] is located in [place], but do not confirm [fact]. "
                    "The missing fact is about [fact]. Query: '[fact]'"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the missing evidence after two hops and generate a precise search query for the third hop.",
                "stage_action": (
                    "First, summarize the key evidence from the first and second hop retrieved passages. "
                    "Then, determine the specific fact missing to verify the claim that has not been confirmed by the evidence. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key evidence has been gathered from the first and second hops? "
                    "What specific fact is still missing?"
                ),
                "example_reasoning": (
                    "The first-hop passages show [fact1] and the second-hop passages show [fact2], but together they do not confirm [fact3]. "
                    "The missing fact is about [fact3]. Query: '[fact3]'"
                ),
                "dependencies": [1, 3],
            },
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing evidence after three hops and generate a precise search query for the fourth hop.",
                "stage_action": (
                    "First, summarize the key evidence from the first, second, and third hop retrieved passages. "
                    "Then, determine the final specific fact missing to verify the claim that has not been confirmed by the evidence. "
                    "This is the last opportunity to retrieve evidence. Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What key evidence has been gathered from all prior retrievals? "
                    "What is the final missing piece of evidence critical for verification?"
                ),
                "example_reasoning": (
                    "All evidence so far supports the claim except for the detail about [fact4]. "
                    "This is the last chance to find evidence for [fact4]. Query: '[fact4]'"
                ),
                "dependencies": [1, 3, 5],
            },
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }