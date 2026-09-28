def entrypoint():
    return {
        "system_prompt": "You are an evidence specialist focused on verifying claims. Your role is to identify and retrieve supporting evidence from Wikipedia. When generating search queries, output ONLY the query string with no additional text, examples, or explanations.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found "
                    "using bullet points."
                ),
                "reasoning_questions": "What specific facts support or contradict the claim? Which entities/events are central to verification?",
                "example_reasoning": "Example summary:\n- Claim: X\n- Retrieved evidence: Y\n- Retrieved evidence: Z\n- Key supporting fact: Y",
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a broad search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Generate a broad search query that includes alternative "
                    "phrasings and related concepts to maximize recall of relevant passages. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific information is still missing? Which entities/relationships need verification?",
                "example_reasoning": "Example: relationship between X and Y",
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from second-hop passages relevant to remaining gaps.",
                "stage_action": (
                    "Read the second-hop passages and identify facts that address the "
                    "previously identified gaps. Summarize the most important evidence found "
                    "using bullet points."
                ),
                "reasoning_questions": "What new facts fill previous gaps? Are there still unanswered questions?",
                "example_reasoning": "Example summary:\n- Retrieved evidence: A\n- Retrieved evidence: B\n- Key fact: A supports the claim",
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Combine evidence and identify gaps",
                "step_type": "llm",
                "aim": "Synthesize all evidence and explicitly enumerate remaining verification gaps.",
                "stage_action": (
                    "Integrate the first-hop and second-hop evidence summaries. Produce a "
                    "comprehensive summary of verified facts using bullet points. Then, list "
                    "ONLY the top two most critical gaps (in order of importance) as specific, "
                    "answerable questions (e.g., '1. What evidence shows that Z occurred?'). "
                    "Format gaps as numbered items."
                ),
                "reasoning_questions": "What has been verified so far? What precise information is still missing? Which gaps are critical for verification?",
                "example_reasoning": "Combined summary:\n- Claim partially verified by X and Y\nGaps:\n1. What evidence shows that Z occurred?\n2. How did W affect the outcome?",
                "dependencies": [2, 5],
            },
            {
                "number": 7,
                "title": "Generate query for gap 1",
                "step_type": "llm",
                "aim": "Generate a precise search query for the first gap identified in step6.",
                "stage_action": (
                    "Based on the first gap (labeled '1.') from step6, generate a concise search query "
                    "that includes specific entity names and relationships. Provide ONLY the search query "
                    "string with no additional text, explanations, or examples."
                ),
                "reasoning_questions": "What specific entities and relationships are mentioned in gap 1? How can we formulate the most precise query for this gap?",
                "example_reasoning": "Example: evidence that smoking causes lung cancer",
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Generate query for gap 2",
                "step_type": "llm",
                "aim": "Generate a precise search query for the second gap identified in step6.",
                "stage_action": (
                    "Based on the second gap (labeled '2.') from step6, generate a concise search query "
                    "that includes specific entity names and relationships. Provide ONLY the search query "
                    "string with no additional text, explanations, or examples."
                ),
                "reasoning_questions": "What specific entities and relationships are mentioned in gap 2? How can we formulate the most precise query for this gap?",
                "example_reasoning": "Example: economic impact of policy X on unemployment",
                "dependencies": [6],
            },
            {
                "number": 9,
                "title": "Retrieve passages for gap 1",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[6]"},
                },
                "dependencies": [7],
            },
            {
                "number": 10,
                "title": "Retrieve passages for gap 2",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }