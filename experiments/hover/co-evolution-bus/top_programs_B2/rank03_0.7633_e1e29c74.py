def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant. Your task is to guide the retrieval of supporting documents for claim verification. Be precise and concise. For query generation steps (Steps 3 and 6), output ONLY the search query string with no additional text, explanations, or formatting.",
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
                "aim": "Extract key entities, dates, and numerical values from the retrieved passages that are relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and identify all entities, dates, and numerical values "
                    "that are directly relevant to verifying the claim. Summarize the evidence by listing "
                    "these structured facts. Omit irrelevant details."
                ),
                "reasoning_questions": (
                    "What are the key entities (people, places, organizations) mentioned? "
                    "What specific dates and numerical values are provided? "
                    "What critical information is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "Retrieved passages mention Tokyo and Japan but not population. "
                    "Relevant facts: [Location: Tokyo, Country: Japan]. "
                    "Missing: population figure for Tokyo in 2020."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing information and generate a focused search query for the second hop.",
                "stage_action": (
                    "Based on the evidence summary, determine the most critical missing piece of "
                    "information needed to verify the claim. Write a concise search query to find "
                    "that information. Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact (entity, date, or number) is missing? "
                    "How can we phrase a query to retrieve that exact fact?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "Evidence summary: [Location: Tokyo, Country: Japan]. "
                    "Missing: population figure for Tokyo in 2020. Query: 'Tokyo population 2020'"
                ),
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
                "aim": "Combine first-hop and second-hop evidence into a structured summary of relevant facts.",
                "stage_action": (
                    "Integrate the first-hop evidence summary with the second-hop passages. "
                    "Extract and list all entities, dates, and numerical values that are relevant to "
                    "the claim. Highlight any remaining gaps."
                ),
                "reasoning_questions": (
                    "What new facts (entities, dates, numbers) were found in the second hop? "
                    "What critical information is still missing? List the missing items specifically."
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "First-hop: [Location: Tokyo, Country: Japan]. "
                    "Second-hop: [Population: 13.96 million (2019)]. "
                    "Relevant facts: [Location: Tokyo, Country: Japan, Population: 13.96 million (2019)]. "
                    "Missing: population for 2020."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the final missing piece of evidence and generate a search query for the third hop.",
                "stage_action": (
                    "This is the last retrieval step. Based on the integrated evidence, determine the "
                    "single most critical missing fact (entity, date, or number) needed to verify "
                    "the claim. Write a concise search query to find that exact fact. Output ONLY "
                    "the search query string with no additional text."
                ),
                "reasoning_questions": (
                    "What is the one critical fact still missing? "
                    "How can we phrase a query to get that specific fact in the final search?"
                ),
                "example_reasoning": (
                    "Example: Claim: 'The population of Tokyo was 14 million in 2020.' "
                    "Integrated evidence: [Location: Tokyo, Country: Japan, Population: 13.96 million (2019)]. "
                    "Missing: population for 2020. Query: 'Tokyo population 2020 official'"
                ),
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
