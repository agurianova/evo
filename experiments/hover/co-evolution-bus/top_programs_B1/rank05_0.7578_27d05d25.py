def entrypoint():
    return {
        "system_prompt": "Multi-hop fact verifier. Analyze evidence gaps between hops. Output ONLY keywords for queries, bullet facts for summaries. Be precise.",
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
                "aim": "Extract critical facts and entities from the first-hop passages relevant to the claim.",
                "stage_action": (
                    "List bullet points of critical facts and entities (names, dates, locations) from the retrieved passages. "
                    "Each bullet must be a concise fact (can be compound if needed). Do not include any analysis or extra text."
                ),
                "reasoning_questions": (
                    "What specific entities (people, organizations, places, dates) are mentioned? "
                    "What factual claims are made that relate to the claim? "
                    "Which facts are critical for verification and might require further evidence?"
                ),
                "example_reasoning": (
                    "Example: \n- John Smith born 1980\n- John Smith won Nobel Prize 2010\n- John Smith worked at MIT until 2015\n- Event X caused Y and Z"
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify critical missing evidence for claim verification and generate a precise second-hop search query.",
                "stage_action": (
                    "Identify the most critical missing piece of evidence for the claim. "
                    "Output ONLY the search query as a string of 3-5 keywords (no quotes, no punctuation, no extra text). "
                    "Include relationship verbs when helpful (e.g., 'Marie Curie born Warsaw'). "
                    "Example: 'Marie Curie nationality'."
                ),
                "reasoning_questions": (
                    "What specific fact from the claim is not yet supported by the first hop? "
                    "Which missing fact is most critical for verifying the claim? "
                    "Should this query focus on an entity relationship or an attribute? "
                    "What 3-5 keywords best capture this for BM25 retrieval?"
                ),
                "example_reasoning": "Example: 'Marie Curie born Warsaw'",
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
                "aim": "Combine evidence from first and second hops into a bullet-point summary of critical facts with explicit missing fact identification.",
                "stage_action": (
                    "Extract key facts from the second-hop passages (each [i] block) and integrate with the first-hop bullet-point summary. "
                    "Output bullet points of critical facts (one fact per bullet, can be compound if needed). "
                    "End with 'Missing fact: [exact unverified fact]' where [exact unverified fact] is the precise statement needed for verification. "
                    "Do not include any analysis or extra text."
                ),
                "reasoning_questions": (
                    "What new critical facts are in the second-hop passages? "
                    "How do they connect to the first-hop facts? "
                    "What is the exact statement that remains unverified and must be confirmed in the third hop?"
                ),
                "example_reasoning": (
                    "Example: \n- John Smith born 1980\n- John Smith won Nobel Prize 2010\n- Jane Doe committee member\n- Jane Doe worked at NIH\nMissing fact: Jane Doe appointed by president in 2010"
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Convert the explicit missing fact into a highly effective BM25 search query.",
                "stage_action": (
                    "Convert the 'Missing fact' statement from previous step into a search query. "
                    "Output ONLY a search query string of 3-5 keywords that captures the core entities and relationship (e.g., 'Jane Doe appointed president 2010' or 'Marie Curie birthplace'). "
                    "Include relationship verbs when helpful for retrieval. No extra text, no quotes, no punctuation."
                ),
                "reasoning_questions": (
                    "Is the missing fact about a relationship between entities or an attribute of a single entity? "
                    "What are the core entities and relationship/attribute that need verification? "
                    "What 3-5 keywords best capture this for BM25 retrieval?"
                ),
                "example_reasoning": "Example: 'Jane Doe appointed president 2010' or 'Marie Curie birthplace Warsaw'",
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
