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
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "What specific facts support or contradict the claim? Which entities/events are central to verification?",
                "example_reasoning": "Example summary: The claim states X. Retrieved passages indicate Y and Z. Key supporting fact: Y.",
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
                    "phrasings and related concepts to maximize recall of relevant passages.\n"
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
                    "previously identified gaps. Summarize the most important evidence found."
                ),
                "reasoning_questions": "What new facts fill previous gaps? Are there still unanswered questions?",
                "example_reasoning": "Example summary: The second-hop passages show A and B. Key fact: A supports the claim.",
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Combine evidence and identify gaps",
                "step_type": "llm",
                "aim": "Synthesize all evidence and explicitly enumerate remaining verification gaps.",
                "stage_action": (
                    "Integrate the first-hop and second-hop evidence summaries. Produce a "
                    "comprehensive summary of verified facts. Then, list SPECIFIC missing "
                    "evidence required to fully verify the claim. Format gaps as numbered items."
                ),
                "reasoning_questions": "What has been verified so far? What precise information is still missing? Which gaps are critical for verification?",
                "example_reasoning": "Combined summary: Claim partially verified by X and Y.\nGaps:\n1. Missing evidence for Z\n2. No information about W",
                "dependencies": [2, 5],
            },
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate precise query for the most critical remaining gap.",
                "stage_action": (
                    "Based on the enumerated gaps, select the highest-priority missing "
                    "evidence. Write a concise, precise search query targeting ONLY this gap.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "Which gap is most critical for verification? How can we formulate the most precise query for this gap?",
                "example_reasoning": "Example: evidence for Z",
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify residual gaps after third hop and generate precise final query.",
                "stage_action": (
                    "Review the third-hop passages against the gap list. Update the gap list by removing any gaps resolved by the third-hop evidence. "
                    "Then, select the highest-priority remaining gap and write a concise, precise search query targeting ONLY this gap.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "Which gaps remain after third hop? What is the minimal query to resolve the last uncertainty?",
                "example_reasoning": "Example: information about W",
                "dependencies": [6, 8],
            },
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }