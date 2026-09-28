def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. When generating search queries, output ONLY the query string with no additional text. When summarizing evidence, be concise and focus on facts relevant to the claim.",
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
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant to verifying the claim. "
                    "Summarize the most important evidence found in a concise paragraph."
                ),
                "reasoning_questions": "What are the key facts about the claim from the retrieved passages? What specific information is still missing to fully verify the claim?",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to fully verify the claim. "
                    "Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: 'Who won the 1975 Cricket World Cup final?'",
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve second-hop passages (deep)",
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
                "aim": "Summarize the second-hop retrieved passages",
                "stage_action": (
                    "Read the retrieved passages and produce a concise summary of the key facts relevant to the claim. "
                    "Focus on evidence that fills the gaps identified in the previous step."
                ),
                "reasoning_questions": "What are the key facts found in the second-hop passages? What specific information is still missing to fully verify the claim?",
                "example_reasoning": "<none>",
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop",
                "stage_action": (
                    "Based on the first-hop summary (step2) and second-hop summary (step5), determine what evidence is still needed to fully verify the claim. "
                    "Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: 'What was the cause of the Chernobyl disaster?'",
                "dependencies": [2, 5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Summarize the third-hop retrieved passages",
                "stage_action": (
                    "Read the retrieved passages and produce a concise summary of the key facts relevant to the claim. "
                    "Focus on evidence that fills the gaps identified in the previous step."
                ),
                "reasoning_questions": "What are the key facts found in the third-hop passages? What specific information is still missing to fully verify the claim?",
                "example_reasoning": "<none>",
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Gap analysis and fourth-hop query",
                "step_type": "llm",
                "aim": "Check for remaining evidence gaps and generate a query for the fourth hop if needed",
                "stage_action": (
                    "Review the first-hop summary (step2), second-hop summary (step5), and third-hop summary (step8). "
                    "If there is still missing evidence needed to verify the claim, write a concise search query to find it. "
                    "If no additional evidence is needed, output an empty string.\n"
                    "Provide ONLY the search query (or empty string), no additional text."
                ),
                "reasoning_questions": "List the required verification facts for the claim. Which of these remain missing after reviewing all evidence? If no gaps, state 'No gaps'.",
                "example_reasoning": "Example: 'What year did the Titanic sink?' OR if no gap: ''",
                "dependencies": [2, 5, 8],
            },
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }