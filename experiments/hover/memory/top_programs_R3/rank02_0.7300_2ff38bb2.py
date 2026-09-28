def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to verify claims by retrieving supporting evidence from Wikipedia. Follow instructions precisely. When asked for a query, output ONLY the query string. When summarizing, be concise and focus on facts relevant to the claim.",
        "steps": [
            # Step 1: First-hop retrieval
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that directly support or refute the claim. "
                    "Produce a concise bullet-point summary of these facts. Focus only on the most relevant evidence."
                ),
                "reasoning_questions": (
                    "1. What specific facts in the passages are directly related to the claim?\n"
                    "2. Are there any contradictions or uncertainties in the evidence?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1889.'\n"
                    "Passages: [1] Paris | The Eiffel Tower, built in 1889, is a famous landmark.\n"
                    "Summary:\n"
                    "- The Eiffel Tower was built in 1889."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the first-hop evidence summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is missing to verify the claim?\n"
                    "2. How can this fact be phrased as a search query?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "First-hop summary:\n"
                    "- Marie Curie won the Nobel Prize in Physics in 1903.\n"
                    "\n"
                    "Query: Marie Curie Nobel Prize Chemistry"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval
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
            # Step 5: Summarize and integrate evidence
            {
                "number": 5,
                "title": "Summarize and integrate evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary and identify gaps.",
                "stage_action": (
                    "Read the first-hop evidence summary (from step2) and the second-hop retrieved passages (from step4). "
                    "First, create a concise bullet-point summary of the second-hop passages. Then, integrate this summary "
                    "with the first-hop summary to form a unified evidence summary. Finally, list any remaining gaps in the evidence."
                ),
                "reasoning_questions": (
                    "1. What new facts are provided in the second-hop passages?\n"
                    "2. How do these new facts relate to the claim and the first-hop evidence?\n"
                    "3. What specific information is still missing?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "First-hop summary:\n"
                    "- Marie Curie won the Nobel Prize in Physics in 1903.\n"
                    "Second-hop passages:\n"
                    "[1] Chemistry | Marie Curie won the Nobel Prize in Chemistry in 1911.\n"
                    "\n"
                    "Second-hop summary:\n"
                    "- Marie Curie won the Nobel Prize in Chemistry in 1911.\n"
                    "Unified summary:\n"
                    "- Marie Curie won two Nobel Prizes: Physics (1903) and Chemistry (1911).\n"
                    "Gaps: None."
                ),
                "dependencies": [2, 4],
            },
            # Step 6: Generate third-hop query conditionally
            {
                "number": 6,
                "title": "Generate third-hop query conditionally",
                "step_type": "llm",
                "aim": "Identify if any gaps remain and generate a search query for the third hop if needed.",
                "stage_action": (
                    "Based on the unified evidence summary (from step5), determine if there is any missing evidence "
                    "required to verify the claim. If gaps remain, write a concise search query to find the missing evidence. "
                    "If no more evidence is needed, output exactly 'NO_QUERY_NEEDED'.\n"
                    "Provide ONLY the query or 'NO_QUERY_NEEDED', no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific fact is still missing (if any)?\n"
                    "2. If a gap exists, how can it be phrased as a search query?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie won two Nobel Prizes.'\n"
                    "Unified summary:\n"
                    "- Marie Curie won two Nobel Prizes: Physics (1903) and Chemistry (1911).\n"
                    "Gaps: None.\n"
                    "\n"
                    "Output: NO_QUERY_NEEDED"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }