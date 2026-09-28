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
                "aim": "Synthesize all evidence and explicitly enumerate up to two critical verification gaps.",
                "stage_action": (
                    "Integrate the first-hop and second-hop evidence summaries. Produce a "
                    "comprehensive summary of verified facts. Then, list up to two SPECIFIC missing "
                    "evidence items required to fully verify the claim, prioritized by criticality. Format gaps as numbered items."
                ),
                "reasoning_questions": "What has been verified so far? What precise information is still missing? Which gaps are critical for verification?",
                "example_reasoning": "Combined summary: Claim partially verified by X and Y.\nGaps:\n1. Missing evidence for Z\n2. No information about W",
                "dependencies": [2, 5],
            },
            {
                "number": 7,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate optimized query covering related gaps or top gap.",
                "stage_action": (
                    "Based on the enumerated gaps (up to two), if the gaps are closely related (e.g., involve the same entities or events), "
                    "generate a single search query that covers both gaps using entity-specific terms. Otherwise, generate a query for the "
                    "highest-priority gap (the first one) using entity-specific terms. For example, instead of 'evidence for Z', use 'evidence "
                    "that [EntityA] caused [EntityB]'.\nProvide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "Are the gaps related? Which entities/relationships should be included for precision?",
                "example_reasoning": "Example: evidence that climate change caused the 2020 Australian bushfires",
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
                "aim": "Generate final query for residual gaps with explicit resolution criteria",
                "stage_action": (
                    "Review the third-hop passages against the gap list from step6. Update the gap list by removing any gaps that are resolved "
                    "(a gap is resolved only if a passage explicitly states the fact required by the gap). If there are no remaining gaps, output "
                    "the string 'NO FURTHER SEARCH NEEDED'. Otherwise, select the highest-priority remaining gap and write a concise, precise "
                    "search query targeting ONLY this gap using entity-specific terms. For example, instead of 'information about W', use 'role of "
                    "[EntityC] in [EventD]'.\nProvide ONLY the search query or the string 'NO FURTHER SEARCH NEEDED', no additional text."
                ),
                "reasoning_questions": "Which gaps remain after third hop? What is the minimal entity-specific query to resolve the last uncertainty?",
                "example_reasoning": "Example 1 (gaps remain): Third-hop passages resolved gap1. Gap2 remains. Query: role of monarch butterflies in pollination\nExample 2 (no gaps): Third-hop passages resolved both gaps. Output: NO FURTHER SEARCH NEEDED",
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