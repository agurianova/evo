def entrypoint():
    return {
        "system_prompt": "You are a precise fact-checking assistant. For summarization steps, focus on extracting relevant facts and identifying missing information. When generating a search query, output ONLY the query string with no additional text or explanations.",
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
                "aim": "Extract key facts from the retrieved passages relevant to the claim and identify missing information.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are relevant to verifying the claim. "
                    "Summarize the key evidence found and explicitly state what information is still missing to verify the claim."
                ),
                "reasoning_questions": "",
                "example_reasoning": "Key facts: Marie Curie was born in Poland and later became a French citizen. Missing: The exact year she moved to France and details of her naturalization process.",
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
                    "Based on the summary, determine what additional evidence is needed to fully verify the claim. "
                    "Write a precise but not overly narrow search query (include key synonyms if applicable) to find the missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "",
                "example_reasoning": "Cause of World War I\nAlbert Einstein birth year\nWorld War II start date",
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
                "aim": "Extract key facts from second-hop passages and combine with first-hop evidence into a comprehensive summary with gap identification.",
                "stage_action": (
                    "Read the second-hop passages (from step 4) and extract key facts relevant to the claim. "
                    "Then, integrate these facts with the first-hop evidence summary (from step 2) to produce a unified evidence summary. "
                    "Cover all relevant facts found so far and explicitly identify any remaining gaps in the evidence."
                ),
                "reasoning_questions": "",
                "example_reasoning": "Key facts: Marie Curie won two Nobel Prizes, one in Physics (1903) and one in Chemistry (1911). Missing: The exact contribution that led to her Chemistry prize and whether she was the sole recipient.",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate a comprehensive search query for the final retrieval step.",
                "stage_action": (
                    "Based on all evidence gathered so far, determine what final piece of evidence is needed to fully verify the claim. "
                    "Write a precise but not overly narrow search query for the last retrieval step (step 7 uses a wider net, so include key synonyms if applicable) to find this evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "",
                "example_reasoning": "Nobel Prize in Physics 1903 details\nMarie Curie Chemistry Nobel Prize year\nMarie Curie Nobel Prize co-recipients",
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
