def entrypoint():
    return {
        "system_prompt": "You are a fact-checker. Be precise: output ONLY the query when instructed.",
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
                "title": "Identify 1-2 distinct second-hop gaps",
                "step_type": "llm",
                "aim": "Extract key facts and identify 1 or 2 distinct missing information gaps for second-hop queries.",
                "stage_action": (
                    "Read all retrieved passages from step1 and identify facts relevant to verifying the claim. "
                    "Then, identify 1 or 2 specific gaps in evidence that are critically needed to fully verify the claim. "
                    "Do not force a second gap if the claim can be verified with one additional fact. "
                    "Format as:\nGap 1: [description]\n[Gap 2: [description]] (if a second gap exists)"
                ),
                "reasoning_questions": "What critical facts are missing? How many gaps are truly needed? Avoid forcing a second gap if one suffices.",
                "example_reasoning": "Example (two gaps): Gap 1: Population data for Paris in 2010\nGap 2: Completion date of Eiffel Tower\n\nExample (one gap): Gap 1: Official source for France's GDP in 2020",
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
                "title": "Generate second second-hop query (conditional)",
                "step_type": "llm",
                "aim": "Generate search query for the second missing information gap if it exists.",
                "stage_action": (
                    "If there is a second gap description (Gap 2) from step2, write a concise search query to find evidence for this gap. "
                    "Otherwise, output nothing (empty string). "
                    "Provide ONLY the search query or empty string, no additional text."
                ),
                "reasoning_questions": "Does a second distinct gap exist? What specific fact is missing?",
                "example_reasoning": "Example (with Gap2): 'Eiffel Tower completion date'\nExample (without Gap2): [empty]",
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
                "title": "Generate first third-hop query (conditional)",
                "step_type": "llm",
                "aim": "Identify critical remaining gap and generate search query if needed.",
                "stage_action": (
                    "After reviewing the first-hop summary (step2 output), first second-hop passages (step5), and second second-hop passages (step6), "
                    "determine if there is a critical missing piece of evidence essential to verify the claim. "
                    "If so, write a precise search query to find this evidence. Otherwise, output nothing (empty string). "
                    "Provide ONLY the search query or empty string, no additional text."
                ),
                "reasoning_questions": "What single fact would most resolve uncertainty? Which entities are central to this gap?",
                "example_reasoning": "Example (with gap): 'France GDP 2020 official figure'\nExample (no gap): [empty]",
                "dependencies": [2, 5, 6],
            },
            {
                "number": 8,
                "title": "Generate second third-hop query (distinct)",
                "step_type": "llm",
                "aim": "Identify distinct critical gap and generate complementary search query.",
                "stage_action": (
                    "After reviewing the first-hop summary (step2 output), first second-hop passages (step5), and second second-hop passages (step6), "
                    "determine if there is another distinct critical missing piece of evidence essential to verify the claim. "
                    "Ensure this gap is distinct from the first by avoiding the same entities and focusing on a different aspect. "
                    "If so, write a precise search query to find this evidence. Otherwise, output nothing (empty string). "
                    "Provide ONLY the search query or empty string, no additional text."
                ),
                "reasoning_questions": "What complementary fact would strengthen verification? How does this gap differ from the first?",
                "example_reasoning": "Example (with gap): 'UN verification of French economic data 2020'\nExample (no gap): [empty]",
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
