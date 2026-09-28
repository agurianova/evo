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
                "aim": "Extract key facts from the retrieved passages relevant to the claim and identify multiple missing information gaps.",
                "stage_action": (
                    "Restate the original claim. Read all retrieved passages and identify facts relevant to verifying the claim. "
                    "Summarize key evidence found and explicitly list multiple specific gaps still missing to verify the claim."
                ),
                "reasoning_questions": "What facts support or contradict the claim? What specific gaps remain that prevent verification?",
                "example_reasoning": "Original claim: Marie Curie became a French citizen. Key facts: Born in Poland, moved to France in 1891. Missing: Exact naturalization year, legal process details, and citizenship status at death. Clues for second hop: moved to France in 1891 implies checking naturalization records.",
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify the most critical missing information (a gap resolvable by a single factual datum) and generate a focused entity-based search query.",
                "stage_action": (
                    "Based on the summary, determine the single most critical missing piece of evidence (a gap resolvable by a single factual datum, e.g., date or location, whose resolution most directly verifies or falsifies the claim). "
                    "Generate a precise entity-focused search query (e.g., 'Marie Curie naturalization year') with ONLY alphanumeric characters and spaces. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": "Which gap, if resolved, most directly confirms/refutes the claim? Why prioritize it over others?",
                "example_reasoning": "Marie Curie naturalization year",
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
                "aim": "Integrate evidence from both hops while maintaining claim context and gap analysis",
                "stage_action": (
                    "Restate the original claim. Read second-hop passages and extract new key facts. "
                    "Integrate these with first-hop evidence into a unified summary. "
                    "Explicitly state how facts relate to the claim, identify remaining gaps, and highlight at least one specific entity or attribute that requires third-hop verification (e.g., 'X founded Y' implies checking Y's founding)."
                ),
                "reasoning_questions": "What new facts were found? How do they relate to the claim? What specific gaps remain, and what entities/attributes suggest third-hop searches?",
                "example_reasoning": "Original claim: Marie Curie became a French citizen. Key facts: Naturalized in 1911 per French archives. Missing: Exact date in 1911, required documents, and whether she retained Polish citizenship. Clues for third hop: 'French archives' suggests checking archival records.",
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify final evidence gap and generate a synonym-enhanced query for deep retrieval",
                "stage_action": (
                    "Based on all evidence, determine the single most critical remaining gap. "
                    "Generate a precise query including key synonyms (e.g., 'Eiffel Tower location Paris La Tour Eiffel') using ONLY alphanumeric characters and spaces. "
                    "Use synonyms from the summary in Step 5 or common entity alternatives (e.g., 'USA' for 'United States') to enhance recall. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": "",
                "example_reasoning": "Marie Curie citizenship naturalization documents french archives",
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
