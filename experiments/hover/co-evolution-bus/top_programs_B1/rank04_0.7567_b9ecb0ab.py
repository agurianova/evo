def entrypoint():
    return {
        "system_prompt": "Fact-checker: Summaries list facts/gaps; queries output ONLY keywords.",
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
                "aim": "Extract key facts and identify gaps from first-hop passages",
                "stage_action": (
                    "List bullet points of key facts and entities (names, dates, locations) from the retrieved passages, one fact per bullet. "
                    "Then list bullet points of missing information needed to verify the claim. "
                    "Do not include any analysis or extra text. Preserve all potentially relevant details for later hops."
                ),
                "reasoning_questions": (
                    "What specific entities (people, organizations, places, dates) are mentioned? "
                    "What factual claims are made that relate to the claim? "
                    "Which facts are critical for verification and what key information is missing?"
                ),
                "example_reasoning": (
                    "Example: \n- Entity: John Smith\n- Fact: Born in 1980\n- Fact: Won Nobel Prize in 2010\n- Fact: Worked at MIT until 2015\n\nGaps:\n- Committee members for 2010 Nobel Prize"
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate precise search query for missing second-hop evidence",
                "stage_action": (
                    "Based on the bullet-point summary, identify the most critical missing piece of evidence needed to "
                    "verify the claim. Output ONLY the search query as a string of plain keywords (e.g., 'John Smith Nobel Prize committee members 2010 affiliations'), "
                    "avoiding any extra text, quotes, or punctuation. Do not include phrases like 'Query:' or 'Keywords:'."
                ),
                "reasoning_questions": (
                    "What specific fact from the claim is not yet supported? "
                    "Which entity or event needs more context? "
                    "What exact terms would find the missing document?"
                ),
                "example_reasoning": (
                    "The claim is that John Smith won the Nobel Prize in 2010. The first-hop summary confirms the win and year but does not mention the committee. "
                    "The missing evidence is the committee members. The most critical missing piece is a committee member's name and affiliation. "
                    "I need to search for terms that would retrieve a document about the 2010 Nobel committee members and their affiliations."
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
                "aim": "Integrate evidence and identify critical final gap",
                "stage_action": (
                    "Extract key facts and entities from the second-hop passages and integrate them with the first-hop summary. "
                    "List bullet points of all key facts and entities, one fact per bullet. "
                    "Then list the single most critical missing piece of evidence required for claim verification. "
                    "Do not include any analysis or extra text."
                ),
                "reasoning_questions": (
                    "What new facts and entities were added in the second hop? "
                    "How do they connect to the first-hop facts? "
                    "What is the single most critical gap remaining for verification?"
                ),
                "example_reasoning": (
                    "Example: \n- Entity: John Smith\n- Fact: Born in 1980\n- Fact: Won Nobel Prize in 2010\n- Fact: Committee member: Jane Doe\n- Fact: Jane Doe worked at NIH\n\nCritical Gap:\n- Jane Doe's role at NIH during 2010"
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate highly specific query for hardest-to-find evidence",
                "stage_action": (
                    "Based on the integrated evidence, identify the single most critical and hardest-to-find missing piece of evidence. "
                    "Output ONLY the search query as a string of 6-8 plain keywords (e.g., 'Jane Doe NIH role 2010 Nobel committee members'), "
                    "avoiding any extra text, quotes, or punctuation. Do not include phrases like 'Query:' or 'Keywords:'."
                ),
                "reasoning_questions": (
                    "What is the one remaining fact that is essential and not yet verified? "
                    "Which entity or relationship is most distant from the claim? "
                    "What exact 6-8 terms would retrieve the needed document?"
                ),
                "example_reasoning": (
                    "The claim requires verification of John Smith's Nobel win. We have evidence of the win, the committee member Jane Doe, and Jane Doe's NIH affiliation. "
                    "The missing evidence is Jane Doe's specific role at NIH during the 2010 committee period and her connection to the Nobel award. "
                    "The most critical missing piece is Jane Doe's title and responsibilities at NIH in 2010. "
                    "I need to search for terms that would retrieve a document about Jane Doe's position at NIH in 2010 and her Nobel committee role."
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
