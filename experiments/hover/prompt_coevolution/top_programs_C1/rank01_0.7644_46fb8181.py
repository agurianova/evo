def entrypoint():
    return {
        "system_prompt": "You are a meticulous fact-checker specializing in multi-hop claim verification. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. Be precise, thorough, and focus only on facts directly relevant to the claim. After each retrieval, identify missing evidence gaps. When generating search queries, use concise keyword phrases without natural language fluff. Always structure your reasoning to answer specific questions and provide only the required output format.",
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
                "reasoning_questions": "What are the key facts in the retrieved passages that directly support or refute the claim? Which facts are most critical for verification? Omit irrelevant details.",
                "example_reasoning": "Example reasoning:\nClaim: 'Marie Curie won two Nobel Prizes in different sciences.'\nRetrieved passages:\n[1] Marie Curie | She was awarded the Nobel Prize in Physics in 1903 and the Nobel Prize in Chemistry in 1911.\n[2] Nobel Prize in Physics | ... \nKey facts: Marie Curie won the Nobel Prize in Physics in 1903 and the Nobel Prize in Chemistry in 1911.",
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
                    "evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is missing to fully verify the claim? How can this fact be expressed as a concise keyword search query?",
                "example_reasoning": "Example reasoning: \nClaim: 'Marie Curie won two Nobel Prizes in different sciences.'\nFirst-hop summary: 'Marie Curie won the Nobel Prize in Physics in 1903 and the Nobel Prize in Chemistry in 1911.'\nMissing information: Confirmation that these prizes were in different sciences and that she is the only person with two Nobel Prizes in two different sciences.\nMarie Curie multiple Nobel Prizes different sciences",
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
                    "all relevant facts found so far."
                ),
                "reasoning_questions": "What new facts are provided in the second-hop passages? How do they integrate with the first-hop summary? What is the current state of evidence for the claim?",
                "example_reasoning": "Example reasoning:\nFirst-hop summary: Marie Curie won the Nobel Prize in Physics in 1903 and Chemistry in 1911.\nSecond-hop passages:\n[1] Nobel Prize facts | Only four people have won multiple Nobel Prizes.\n[2] Marie Curie biography | She is the only person to win in two different sciences.\nIntegrated evidence: Marie Curie won two Nobel Prizes in different sciences (Physics and Chemistry) and is the only person to achieve this.",
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
                    "search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "What specific fact is still missing to fully verify the claim? How can this fact be expressed as a concise keyword search query?",
                "example_reasoning": "Example reasoning: \nClaim: 'Marie Curie won two Nobel Prizes in different sciences.'\nEvidence so far: She won the Nobel Prize in Physics in 1903 and Chemistry in 1911, which are different sciences. However, we need to confirm if she is the only person to have achieved this.\nlist of people with multiple Nobel Prizes different sciences",
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
