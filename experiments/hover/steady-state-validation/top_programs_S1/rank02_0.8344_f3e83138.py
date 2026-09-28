def entrypoint():
    return {
        "system_prompt": "You are a fact-checker. Be precise: output ONLY the query when instructed.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Identify two distinct second-hop gaps",
                "step_type": "llm",
                "aim": "Extract key facts and identify two distinct missing information gaps for second-hop queries.",
                "stage_action": (
                    "Read all retrieved passages from step1 and identify facts relevant to verifying the claim. "
                    "Then, clearly state two specific gaps in evidence that are needed to fully verify the claim. "
                    "Format as:\nGap 1: [description]\nGap 2: [description]"
                ),
                "reasoning_questions": "What critical facts are missing? Which entities require additional evidence?",
                "example_reasoning": "Example: Gap 1: Population data for Paris in 2010\nGap 2: Completion date of Eiffel Tower",
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Generate search query for the first missing information gap.",
                "stage_action": (
                    "Based on the first gap description (Gap 1) from step2, write a concise search query to find evidence for this gap. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities are involved?",
                "example_reasoning": "Example: 'Paris population 2010'",
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Generate search query for the second missing information gap.",
                "stage_action": (
                    "Based on the second gap description (Gap 2) from step2, write a concise search query to find evidence for this gap. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing? Which entities are involved?",
                "example_reasoning": "Example: 'Eiffel Tower completion date'",
                "dependencies": [2],
            },
            {
                "number": 5,
                "title": "Retrieve first second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},  # Step3 output
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Retrieve second second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},  # Step4 output
                },
                "dependencies": [4],
            },
            {
                "number": 7,
                "title": "Generate first third-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical remaining information gap and generate a search query.",
                "stage_action": (
                    "After reviewing the first-hop summary (step2 output), first second-hop passages (step5), and second second-hop passages (step6), "
                    "determine the most critical missing piece of evidence essential to verify the claim. "
                    "Write a precise search query to find this evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What single fact would most resolve uncertainty? Which entities are central to this gap?",
                "example_reasoning": "Example: 'France GDP 2020 official figure'",
                "dependencies": [2, 5, 6],
            },
            {
                "number": 8,
                "title": "Generate second third-hop query",
                "step_type": "llm",
                "aim": "Identify another distinct critical information gap and generate a search query.",
                "stage_action": (
                    "After reviewing the first-hop summary (step2 output), first second-hop passages (step5), and second second-hop passages (step6), "
                    "determine another distinct critical missing piece of evidence essential to verify the claim. "
                    "Write a precise search query to find this evidence. Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What complementary fact would strengthen verification? How does this gap differ from the first?",
                "example_reasoning": "Example: 'UN verification of French economic data 2020'",
                "dependencies": [2, 5, 6],
            },
            {
                "number": 9,
                "title": "Retrieve first third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},  # Step7 output
                },
                "dependencies": [7],
            },
            {
                "number": 10,
                "title": "Retrieve second third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},  # Step8 output
                },
                "dependencies": [8],
            },
        ],
    }
