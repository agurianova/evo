def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checking assistant. Your primary goal is to maximize the retrieval of relevant evidence by generating precise, multi-term search queries at each hop. Always base your queries on the evidence gathered so far and identify the most critical missing information. Provide ONLY the search query when asked.",
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
                "aim": "Identify the most critical missing evidence after the first hop and generate a search query.",
                "stage_action": "Based on the first-hop passages, determine what specific evidence is missing to verify the claim. Write a concise search query to find that evidence. If multiple gaps exist, combine them with OR (e.g., 'term1 OR term2'). Provide ONLY the search query, no additional text.",
                "reasoning_questions": "What specific fact or evidence mentioned in the claim is not addressed by the first-hop passages?",
                "example_reasoning": "The claim states that 'X causes Y'. The first-hop passages discuss X and Y separately but do not link them. Therefore, the query should be: 'X AND Y AND causes'.",
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
                "aim": "Identify the most critical remaining gap after two hops and generate a targeted search query.",
                "stage_action": "Given the evidence from the first and second hops, identify the most critical remaining gap. Write a search query that targets this gap, using OR to combine multiple possibilities if needed. Provide ONLY the search query, no additional text.",
                "reasoning_questions": "What key element of the claim is still unverified by the combined evidence from the first two hops?",
                "example_reasoning": "So far we have evidence that X is related to Y, but the claim specifies that X causes Y in a particular context (Z). The query should focus on: 'X causes Y in Z OR X leads to Y in Z'.",
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
                "aim": "Identify the final missing evidence after three hops and generate a highly specific search query.",
                "stage_action": "After three hops of evidence, what final piece of evidence is still missing to fully verify the claim? Write a highly targeted search query to find it, using OR to cover alternative formulations. Provide ONLY the search query, no additional text.",
                "reasoning_questions": "What is the last unverified component of the claim that would allow for full verification?",
                "example_reasoning": "We have confirmed X causes Y, but the claim also states the effect size is large. The query should be: 'X causes Y effect size large OR magnitude of X on Y'.",
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