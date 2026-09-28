def entrypoint():
    return {
        "system_prompt": (
            "You are an expert fact-checker specializing in multi-hop evidence retrieval. "
            "Your goal is to retrieve all relevant Wikipedia passages that support or refute the claim. "
            "Follow these principles: "
            "1. Break down complex claims into sub-questions. "
            "2. When generating search queries, use precise, information-seeking phrases that target missing evidence. "
            "3. When summarizing evidence, be concise and highlight facts directly relevant to the claim. "
            "4. Always prioritize retrieving passages that fill specific gaps in the evidence chain."
        ),
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
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from first-hop passages and identify initial gaps.",
                "stage_action": (
                    "Read all retrieved passages and identify facts relevant to verifying the claim. "
                    "Summarize the most important evidence found and specify what aspects remain unaddressed."
                ),
                "reasoning_questions": (
                    "What are the key facts in these passages? "
                    "How do they relate to the claim? "
                    "What aspects of the claim remain unaddressed?"
                ),
                "example_reasoning": (
                    "Passage [1] states that 'X is true'. This supports the claim's first part. "
                    "Passage [2] mentions 'Y', which is unrelated. The claim also requires evidence about Z, which is missing."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate broad search query for second hop based on initial gaps.",
                "stage_action": (
                    "Based on the first-hop summary, identify the broadest missing aspect of the claim. "
                    "Generate a search query that covers this aspect comprehensively. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Combine first and second hop evidence",
                "step_type": "llm",
                "aim": "Integrate first-hop summary with second-hop passages into unified evidence summary.",
                "stage_action": (
                    "Combine the first-hop evidence summary with the newly retrieved second-hop passages. "
                    "Produce a unified evidence summary covering all relevant facts found so far and identify remaining gaps."
                ),
                "reasoning_questions": (
                    "What new facts were found in the second-hop passages? "
                    "How do they connect with the first-hop evidence? "
                    "What gaps still remain in the evidence for the claim?"
                ),
                "example_reasoning": (
                    "First-hop showed X. Second-hop passage [1] provides Y, which connects X to Z. "
                    "However, the claim also requires evidence about W, which is still missing."
                ),
                "dependencies": [2, 4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate specific search query for third hop based on unified summary.",
                "stage_action": (
                    "Based on the unified evidence summary, identify the most specific missing detail. "
                    "Generate a precise search query targeting that exact detail. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Combine all evidence and identify gaps",
                "step_type": "llm",
                "aim": "Create comprehensive evidence summary and identify any remaining gaps.",
                "stage_action": (
                    "Integrate the unified two-hop evidence summary with the third-hop passages. "
                    "Produce a complete evidence summary and precisely list any remaining gaps."
                ),
                "reasoning_questions": (
                    "What critical evidence was found in the third-hop passages? "
                    "How does it complete (or fail to complete) the evidence chain for the claim? "
                    "List any remaining gaps with high precision."
                ),
                "example_reasoning": (
                    "The third-hop passage [3] states 'Z is caused by W', which fills the last gap. "
                    "Now the evidence chain is complete: X -> Y -> Z -> W. No gaps remain."
                ),
                "dependencies": [5, 7],
            },
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Decide if fourth hop is needed and generate query if so.",
                "stage_action": (
                    "Based on the comprehensive evidence summary, determine if the evidence is complete. "
                    "If a critical gap remains, generate a highly specific search query for the missing piece. "
                    "If the evidence is sufficient, output exactly: 'NO_HOPS_NEEDED'. "
                    "Provide ONLY the query or 'NO_HOPS_NEEDED', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [8],
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