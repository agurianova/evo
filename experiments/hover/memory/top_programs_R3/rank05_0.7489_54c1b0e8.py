def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant Wikipedia passages. At each step, follow the instructions precisely. When asked to output a search query, provide ONLY the query string with no additional text.",
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
                    "Read all retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "What are the key facts in the retrieved passages that directly relate to the claim? "
                    "Which facts are most relevant for verification? "
                    "Are there any contradictions in the evidence?"
                ),
                "example_reasoning": (
                    "The claim is: 'The first moon landing was in 1969.'\n"
                    "Retrieved passages: [1] Apollo 11 | The Apollo 11 mission landed on the moon in 1969. [2] Space Race | The US won the space race with the 1969 moon landing.\n"
                    "Key facts: The moon landing occurred in 1969 (from both passages). This directly supports the claim. No contradictions."
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
                    "Based on the summary of the first-hop evidence, determine what additional evidence is needed to "
                    "fully verify the claim. Write a concise search query to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is missing to verify the claim? "
                    "What entities or events should the next query focus on? "
                    "How can we phrase the query to get the missing information?"
                ),
                "example_reasoning": (
                    "Claim: 'The first moon landing was in 1969.'\n"
                    "First-hop summary: Confirms the year 1969 but does not mention the mission name.\n"
                    "Missing fact: the mission name (Apollo 11).\n"
                    "Query: 'Apollo 11 moon landing year'"
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
            # Step 5: Summarize second-hop evidence (NEW)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the second-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that are relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "What are the key facts in the retrieved passages that directly relate to the claim? "
                    "Which facts are most relevant for verification? "
                    "Are there any contradictions in the evidence?"
                ),
                "example_reasoning": (
                    "The claim is: 'The first moon landing was in 1969.'\n"
                    "Retrieved passages: [1] Apollo program | Apollo 11 was the first mission to land humans on the moon. [2] Neil Armstrong | Armstrong was the first person to step on the moon during Apollo 11.\n"
                    "Key facts: Apollo 11 was the mission that landed humans on the moon. This supports the claim by naming the mission. No contradictions."
                ),
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a search query for the third hop.",
                "stage_action": (
                    "Based on the summary of the first-hop evidence and the summary of the second-hop evidence, "
                    "determine what additional evidence is needed to fully verify the claim. "
                    "Write a concise search query to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact is still missing to verify the claim? "
                    "What entities or events should the next query focus on? "
                    "How can we phrase the query to get the missing information?"
                ),
                "example_reasoning": (
                    "Claim: 'The first moon landing was in 1969.'\n"
                    "First-hop summary: Confirms the year 1969.\n"
                    "Second-hop summary: Confirms the mission name Apollo 11.\n"
                    "Missing fact: the exact date (July 20, 1969) or the location (Sea of Tranquility).\n"
                    "Query: 'Apollo 11 moon landing date'"
                ),
                "dependencies": [2, 5],
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