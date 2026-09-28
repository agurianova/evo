def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your goal is to maximize retrieval coverage by identifying all gold supporting documents. Focus on generating queries that capture alternative phrasings of missing information to ensure comprehensive evidence retrieval.",
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
                "aim": "Extract key facts from the retrieved passages relevant to the claim and identify evidence gaps.",
                "stage_action": (
                    "Read all retrieved passages and identify facts directly relevant to verifying the claim. "
                    "Summarize the most important evidence found. If no relevant facts are found, state 'Missing: [specific gap]' "
                    "with precise missing information (e.g., 'Missing: construction dates of Eiffel Tower'). "
                    "Never suggest rephrased claims - only report evidence or gaps."
                ),
                "reasoning_questions": (
                    "What are the key entities and relationships mentioned? "
                    "What evidence directly supports or contradicts the claim? "
                    "What specific information is missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1889.'\n"
                    "Retrieved passages:\n"
                    "[1] Eiffel Tower | Construction began in 1887 and was completed in 1889 for the World's Fair.\n"
                    "[2] ... (other passages)\n"
                    "Reasoning: The claim states the Eiffel Tower was built in 1889. Passage [1] confirms construction was completed in 1889. Relevant facts: Construction started 1887, completed 1889.\n\n"
                    "Claim: 'The Eiffel Tower was built in 1889.'\n"
                    "Retrieved passages:\n"
                    "[1] Paris | Capital of France.\n"
                    "[2] ... (no mention of Eiffel Tower)\n"
                    "Reasoning: None of the passages mention the Eiffel Tower or its construction. Missing: construction dates of Eiffel Tower"
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate diverse search queries to capture alternative expressions of missing evidence.",
                "stage_action": (
                    "Based on the evidence gaps, generate 2-3 alternative search queries that capture different phrasings "
                    "of the missing information, combined with OR (e.g., 'query1 OR query2 OR query3'). "
                    "Focus on precise missing elements from the gap analysis. "
                    "Provide ONLY the combined query string, no additional text."
                ),
                "reasoning_questions": (
                    "What exact information is missing to verify the claim? "
                    "What are 2-3 different ways to phrase this missing information? "
                    "Which phrasing variations are most likely to appear in Wikipedia abstracts?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1889.'\n"
                    "Summary: 'Construction started 1887, completed 1889.'\n"
                    "Missing: Exact completion date.\n"
                    "Eiffel Tower completion date OR Eiffel Tower finished year OR when was Eiffel Tower completed"
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
                "aim": "Combine first-hop and second-hop evidence into a comprehensive summary.",
                "stage_action": (
                    "Integrate the first-hop evidence summary with the newly retrieved second-hop passages. "
                    "Reconcile any conflicting information and identify remaining gaps in evidence. "
                    "If the second-hop passages do not provide relevant information to fill the gap identified in the first-hop summary, "
                    "state that the second-hop was unhelpful and restate the original gap. "
                    "Produce a unified evidence summary covering all relevant facts found so far, or note the lack of progress."
                ),
                "reasoning_questions": (
                    "What new evidence was found in the second-hop? "
                    "How does it connect to the first-hop evidence? "
                    "Are there remaining gaps?"
                ),
                "example_reasoning": (
                    "First-hop summary: Construction started 1887, completed 1889.\n"
                    "Second-hop passages:\n"
                    "[1] Eiffel Tower completion | The tower was completed on March 31, 1889.\n"
                    "Reasoning: The second-hop passage provides the exact completion date (March 31, 1889). Unified summary: Construction started 1887, completed March 31, 1889. No gaps.\n\n"
                    "First-hop summary: Construction started 1887, completed 1889.\n"
                    "Second-hop passages:\n"
                    "[1] Paris weather | The weather in Paris is mild.\n"
                    "[2] ... (irrelevant passages)\n"
                    "Reasoning: The second-hop passages are about Paris weather and not relevant to the construction date. The second-hop did not provide useful information. Remaining gap: exact completion date."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate diverse search queries for final evidence gaps using broader phrasing.",
                "stage_action": (
                    "Based on remaining evidence gaps, generate 2-3 alternative search queries capturing different phrasings "
                    "of the missing information, combined with OR (e.g., 'query1 OR query2 OR query3'). "
                    "Consider the deeper search (k=10) will be performed. "
                    "Provide ONLY the combined query string, no additional text."
                ),
                "reasoning_questions": (
                    "What final piece of evidence is missing? "
                    "What are 2-3 different ways to phrase this missing information? "
                    "Which phrasing variations might appear in less obvious Wikipedia abstracts?"
                ),
                "example_reasoning": (
                    "Claim: 'The Eiffel Tower was built in 1889.'\n"
                    "Summary: 'Construction began in 1887 and took 2 years.'\n"
                    "Missing: Final completion date and opening ceremony.\n"
                    "Eiffel Tower completion date OR Eiffel Tower inauguration year OR when was Eiffel Tower opened"
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
