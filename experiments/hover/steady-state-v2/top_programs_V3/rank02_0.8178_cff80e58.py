def entrypoint():
    return {
        "system_prompt": "You are an evidence verifier. Always prioritize recall for multi-hop claims. Focus on finding all supporting documents. Provide only the required output without any additional text.",
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
                "reasoning_questions": "What are the key entities and relationships mentioned in the passages? Which facts directly support or contradict the claim?",
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built to commemorate the 100th anniversary of the French Revolution.' Passages: [1] Eiffel Tower | ... built in 1889 ... [2] French Revolution | ... occurred in 1789 ... Summary: The Eiffel Tower was built in 1889. The French Revolution occurred in 1789. The 100th anniversary would be 1889, so the claim is plausible but the passages do not explicitly state the reason for construction.",
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a search query for the second hop.",
                "stage_action": (
                    "Based on the summary, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing "
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific information is missing from the first-hop evidence to verify the claim? Which entities or relationships need to be connected?",
                "example_reasoning": "Example: Claim: 'The Eiffel Tower was built to commemorate the 100th anniversary of the French Revolution.' First-hop evidence: [1] Eiffel Tower | ... built in 1889 ... [2] French Revolution | ... occurred in 1789 ... Missing: The reason for building the Eiffel Tower. Query: 'Why was the Eiffel Tower built?'",
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
                "title": "Summarize first and second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence (from raw passages) with the newly retrieved "
                    "second-hop passages. Produce a unified evidence summary covering "
                    "all relevant facts found so far."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what final piece "
                    "of evidence is needed to fully verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "Given the first-hop and second-hop evidence, what final piece of information is required to verify the claim? What gap remains?",
                "example_reasoning": "Example: Claim: 'Marie Curie was the first woman to win a Nobel Prize.' First-hop: [1] Marie Curie | ... won Nobel Prize in 1903 ... Second-hop: [1] Nobel Prize | ... first awarded in 1901 ... Missing: Confirmation that no woman won before 1903. Query: 'Was there a woman Nobel Prize winner before Marie Curie?'",
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
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the third-hop retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": "What are the key entities and relationships in these passages? How do they connect to the claim and previous evidence?",
                "example_reasoning": "Example: Claim: 'Marie Curie was the first woman to win a Nobel Prize.' Passages: [1] List of Nobel laureates | ... 1901: Wilhelm Röntgen (Physics) ... 1903: Marie Curie (Physics) ... Summary: The first Nobel Prizes were awarded in 1901. Marie Curie won in 1903. No woman won in 1901 or 1902.",
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing evidence and generate a search query for the fourth hop.",
                "stage_action": (
                    "Based on all evidence gathered so far (from first, second, and third hops), "
                    "identify the final piece of evidence needed to verify the claim. Write a concise "
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "Given the integrated evidence summary and the third-hop evidence, what specific fact is still missing to verify the claim? What query would find it?",
                "example_reasoning": "Example: Claim: 'Marie Curie was the first woman to win a Nobel Prize.' Integrated evidence: Marie Curie won in 1903. Nobel Prizes started in 1901. Missing: Confirmation no woman won between 1901-1903. Query: 'List of women Nobel Prize winners before 1903'",
                "dependencies": [5, 8],
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