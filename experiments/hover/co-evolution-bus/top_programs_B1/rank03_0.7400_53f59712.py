def entrypoint():
    return {
        "system_prompt": "Expert fact-checker: For evidence summaries, output bullet-point facts only. For query steps, output ONLY the search query string.",
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
                "aim": "Extract key facts and entities from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Extract all key facts and entities (people, places, dates, etc.) from the retrieved passages that are relevant to the claim. "
                    "Present as a bullet-point list of concise, verifiable facts. Do not include any reasoning or extra text."
                ),
                "reasoning_questions": (
                    "1. What are the key entities (names, locations, organizations) mentioned in the passages?\n"
                    "2. What specific facts about these entities are relevant to the claim?\n"
                    "3. Are there any dates, numbers, or specific details that could help verify the claim?"
                ),
                "example_reasoning": (
                    "Example reasoning for claim 'Marie Curie was born in Paris':\n"
                    "- Passages mention 'born in Warsaw' and 'moved to Paris'\n"
                    "- Key entities: Marie Curie\n"
                    "- Critical fact: birthplace is Warsaw (contradicts claim)\n"
                    "- Must preserve both birthplace and relocation facts for later hops\n"
                    "Output:\n"
                    "- Marie Curie was born in Warsaw (source: passage 1)\n"
                    "- Marie Curie moved to Paris for study (source: passage 2)"
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify a specific missing piece of evidence needed to verify the claim and generate a precise search query.",
                "stage_action": (
                    "Based on the bullet-point evidence summary, identify the most critical missing piece of information required to verify the claim. "
                    "Formulate a concise search query (3-5 keywords) that targets this specific gap. Output ONLY the search query, nothing else."
                ),
                "reasoning_questions": (
                    "1. What fact from the summary directly supports or contradicts the claim?\n"
                    "2. What specific information is still missing to fully verify the claim?\n"
                    "3. Which entity or relationship should the next search focus on?"
                ),
                "example_reasoning": (
                    "Example for claim 'Marie Curie was born in Paris':\n"
                    "Evidence shows birthplace Warsaw but claim says Paris.\n"
                    "Missing: Official documentation of birthplace.\n"
                    "Critical gap: Birth certificate location.\n"
                    "Output ONLY:\n"
                    "Marie Curie birth certificate location"
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
                "aim": "Combine evidence from both hops into a comprehensive, non-redundant summary of key facts relevant to the claim.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (step 2) with the newly retrieved second-hop passages. "
                    "Extract all key facts and entities, resolving contradictions and noting sources. "
                    "Present as a bullet-point list of concise, verifiable facts. Do not include reasoning or extra text."
                ),
                "reasoning_questions": (
                    "1. What new facts from the second-hop passages relate to the claim?\n"
                    "2. How do these new facts interact with the first-hop evidence (support, contradict, or add context)?\n"
                    "3. What is the current state of evidence for verifying the claim?"
                ),
                "example_reasoning": (
                    "Example for claim 'Marie Curie was born in Paris':\n"
                    "First-hop: birthplace Warsaw, moved to Paris\n"
                    "Second-hop: 'birth certificate issued in Warsaw'\n"
                    "Integration: Both hops confirm Warsaw birthplace\n"
                    "Output:\n"
                    "- Marie Curie was born in Warsaw (sources: passage 1, second-hop passage 1)\n"
                    "- Marie Curie moved to Paris for study (source: passage 2)"
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the single most critical missing piece of evidence required to verify the claim, and generate a highly specific search query.",
                "stage_action": (
                    "Based on the integrated evidence summary, identify the one remaining gap that, if filled, would allow full verification of the claim. "
                    "Formulate a very precise search query (3-5 keywords) targeting ONLY this gap. Output ONLY the search query string, nothing else."
                ),
                "reasoning_questions": (
                    "1. What is the current state of evidence: what has been confirmed and what is still missing?\n"
                    "2. What specific fact or document would definitively confirm or refute the claim?\n"
                    "3. Which entity, date, or relationship is the linchpin for verification?"
                ),
                "example_reasoning": (
                    "Example for claim 'Marie Curie was born in Paris':\n"
                    "Evidence strongly confirms Warsaw birthplace from multiple sources.\n"
                    "Remaining gap: Official government record to be 100% certain.\n"
                    "Critical gap: Polish civil registry documentation.\n"
                    "Output ONLY:\n"
                    "Polish civil registry Marie Curie birth"
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
