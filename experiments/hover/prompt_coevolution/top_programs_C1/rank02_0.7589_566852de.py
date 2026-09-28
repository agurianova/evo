def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. Be precise, thorough, and focus only on facts directly relevant to the claim. Always structure your reasoning to answer specific questions and provide only the required output format. In multi-hop verification, each step must identify missing information gaps and generate concise, keyword-rich search queries without natural language fluff.",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "What specific facts in the passages directly support or refute the claim?\nAre there any critical details missing that would be needed to verify the claim?",
                "example_reasoning": "Example reasoning:\nClaim: 'The Eiffel Tower was originally intended to be a temporary structure.'\nPassages: [1] Eiffel Tower | Construction of the Eiffel Tower began in 1887 and was completed in 1889. It was built as the entrance arch for the 1889 World's Fair.\nKey facts: The Eiffel Tower was built for the 1889 World's Fair. Missing information: The intended duration (temporary or permanent) of the structure is not stated.",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n\nCRITICAL: Your output must be EXACTLY the search query string "
                    "with no additional text, not even a single extra character or newline. "
                    "Output only the query."
                ),
                "reasoning_questions": "What exact fact is missing to verify the claim?\nWhat keywords would best capture the missing fact for a search engine?",
                "example_reasoning": "Example reasoning:\nClaim: 'The Eiffel Tower was originally intended to be a temporary structure.'\nFirst-hop summary: 'The Eiffel Tower was built for the 1889 World's Fair.'\nMissing information: The intended duration (temporary or permanent) of the structure is not stated.\nthe eiffel tower temporary structure intended duration",
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary with the newly retrieved "
                    "second-hop passages. Produce a unified evidence summary covering "
                    "all relevant facts found so far. Then, explicitly state any remaining "
                    "gaps under the heading 'Remaining Gap:'."
                ),
                "reasoning_questions": "What new facts did the second-hop passages add?\nDo the combined facts now fully support or refute the claim? If not, what is still missing? Format the missing information under 'Remaining Gap:'.",
                "example_reasoning": "Example reasoning:\nClaim: 'The Eiffel Tower was originally intended to be a temporary structure.'\nFirst-hop summary: The Eiffel Tower was built for the 1889 World's Fair.\nSecond-hop passages: [1] World's Fair | The 1889 World's Fair in Paris celebrated the 100th anniversary of the French Revolution.\nUnified summary: The Eiffel Tower was built as the entrance arch for the 1889 World's Fair in Paris, which celebrated the 100th anniversary of the French Revolution.\nRemaining Gap: The intended duration (temporary or permanent) of the Eiffel Tower is not stated.",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n\nCRITICAL: Your output must be EXACTLY "
                    "the search query string with no additional text, not even a single "
                    "extra character or newline. Output only the query."
                ),
                "reasoning_questions": "Considering evidence from both first and second hops, what specific fact is still missing to verify the claim?\nHow can you formulate a precise search query that captures this missing fact, given the context of two hops of evidence?",
                "example_reasoning": "Example reasoning:\n[Output from Step 5]:\nUnified summary: The Eiffel Tower was built as the entrance arch for the 1889 World's Fair in Paris, which celebrated the 100th anniversary of the French Revolution.\nRemaining Gap: The intended duration (temporary or permanent) of the Eiffel Tower is not stated.\nMissing information: Confirmation of the Eiffel Tower's intended permanence status.\nthe eiffel tower temporary structure intended duration",
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
