def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert verifying claims by retrieving evidence from Wikipedia. Your goal is to find all relevant evidence to support or refute the claim. Use multi-hop reasoning: after initial retrieval, identify multiple independent gaps in evidence and generate separate queries for parallel evidence branches. When generating queries, focus on one specific missing fact per query and output ONLY the search query.",
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
                "title": "Generate branch A query",
                "step_type": "llm",
                "aim": "Identify the first critical missing evidence after first hop and generate precise search query for second hop (branch A).",
                "stage_action": (
                    "Based on the first-hop retrieved passages, determine the most important specific fact missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the most critical fact missing from the first-hop evidence? "
                    "Which entity or relationship is most essential to verify next?"
                ),
                "example_reasoning": (
                    "The claim states 'X'. The first-hop passages mention Y but do not confirm Z, which is required for verification. "
                    "Therefore, the missing fact is about Z. Query: 'Z'"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve branch A passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate branch B query",
                "step_type": "llm",
                "aim": "Identify a different critical missing evidence (independent of branch A) and generate precise search query for second hop (branch B).",
                "stage_action": (
                    "Based solely on the first-hop retrieved passages (ignoring branch A results), determine another important specific fact missing to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is another critical fact missing from the first-hop evidence that is distinct from branch A's focus? "
                    "Which other entity or relationship needs verification?"
                ),
                "example_reasoning": (
                    "The first-hop passages mention Y but do not confirm Z (addressed by branch A) and also do not address W, another critical aspect. "
                    "Therefore, the missing fact for branch B is about W. Query: 'W'"
                ),
                "dependencies": [1],
            },
            {
                "number": 5,
                "title": "Retrieve branch B passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate final-hop query",
                "step_type": "llm",
                "aim": "Identify the last missing evidence after gathering all prior evidence and generate precise search query for third hop.",
                "stage_action": (
                    "Based on all evidence from first hop and both second-hop branches, determine the final piece of evidence needed to verify the claim. "
                    "Write a concise search query to find that evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the absolute last missing fact? Has all other evidence been gathered? "
                    "Which specific detail is still absent and critical?"
                ),
                "example_reasoning": (
                    "All evidence so far supports the claim except for the detail about D. "
                    "This is the last opportunity to find confirming evidence. Query: 'D'"
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