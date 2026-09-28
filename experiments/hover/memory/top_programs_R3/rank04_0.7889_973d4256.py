def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to verify claims by retrieving all relevant evidence from Wikipedia. At each step, focus on identifying missing evidence and generating precise search queries to maximize the retrieval of supporting documents. Always output only the search query when instructed to do so.",
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
                "aim": "Identify missing evidence after first hop and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the retrieved passages, determine what additional evidence is needed to verify the claim. "
                    "Write a concise search query to find the missing evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to support or refute the claim? "
                    "What entities or relationships should the next query target?"
                ),
                "example_reasoning": (
                    "The claim states that X caused Y. The first-hop passages mention X and Y but do not establish causation. "
                    "Therefore, the next query should search for evidence of causation between X and Y, e.g., 'X effect on Y'."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify residual gaps after two hops and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what additional evidence is still missing to fully verify the claim. "
                    "Write a concise search query to find this evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What is the remaining gap in the evidence chain? "
                    "What specific piece of information would close this gap? "
                    "Consider alternative search terms if the evidence is elusive."
                ),
                "example_reasoning": (
                    "After two hops, we have evidence that X and Y are correlated but not that X causes Y. "
                    "We need evidence of a causal mechanism. The next query should search for 'mechanism of X causing Y' or similar."
                ),
                "dependencies": [1, 3],
            },
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify final gaps after three hops and generate a search query for the fourth hop.",
                "stage_action": (
                    "Based on all evidence gathered from three hops, determine the final piece of evidence needed to verify the claim. "
                    "Write a concise search query to find this evidence. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "Is the claim fully supported by the evidence? "
                    "If not, what is the last missing piece? "
                    "If the evidence is contradictory, what query would resolve the conflict?"
                ),
                "example_reasoning": (
                    "We have three pieces of evidence: X and Y are correlated, there is a plausible mechanism, "
                    "but no direct intervention study. The final query should search for 'interventional study X Y'."
                ),
                "dependencies": [1, 3, 5],
            },
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }