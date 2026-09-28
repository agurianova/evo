def entrypoint():
    return {
        "system_prompt": "You are an evidence retrieval assistant specialized in multi-hop claim verification. Your role is to analyze claims, extract precise facts from retrieved passages, and generate focused search queries to gather missing evidence. Always prioritize factual accuracy, relevance to the claim, and concise output. For query generation steps, output ONLY the search query string without any additional text.",
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
                "aim": "Extract precise, claim-relevant facts from the first-hop passages to support verification.",
                "stage_action": "Read the retrieved passages and extract specific entities, dates, numerical values, and key relationships. Omit general background. Format as a structured list of facts.",
                "reasoning_questions": "What specific entities (people, places, organizations) are mentioned? What exact dates or numerical values are provided? What information is still missing to verify the claim?",
                "example_reasoning": "",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information and generate a precise second-hop search query.",
                "stage_action": "Based on the summary, determine what additional evidence is needed to fully verify the claim. Write a concise search query to find the missing evidence.\nProvide ONLY the search query, no additional text.",
                "reasoning_questions": "",
                "example_reasoning": "Example:\nClaim: 'Marie Curie won her first Nobel Prize in 1903.'\nFirst-hop summary: ['Marie Curie was a physicist.', 'She conducted pioneering research on radioactivity.']\nMissing: year of first Nobel Prize\nMarie Curie first Nobel Prize year",
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
                "aim": "Integrate first-hop and second-hop evidence into a comprehensive, structured summary of claim-relevant facts.",
                "stage_action": "Combine the first-hop summary and the second-hop passages. Extract specific entities, dates, numerical values, and key relationships. Omit redundant or irrelevant details. Format as a structured list of facts covering all evidence.",
                "reasoning_questions": "What new facts were added by the second-hop passages? What specific entities, dates, or numerical values are now known? What critical information is still missing to verify the claim?",
                "example_reasoning": "",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the final critical missing evidence and generate a precise third-hop search query (last opportunity).",
                "stage_action": "This is the final retrieval step. Identify the single most critical missing piece of evidence required to verify the claim. Write a concise search query to find it. Provide ONLY the search query, no additional text.",
                "reasoning_questions": "",
                "example_reasoning": "Example:\nClaim: 'The first moon landing occurred on July 20, 1969.'\nCurrent evidence: ['Apollo 11 launched on July 16, 1969.', 'The lunar module landed on the Moon.']\nMissing: exact date of moon landing\nApollo 11 moon landing date",
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
