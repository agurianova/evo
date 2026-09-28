def entrypoint():
    return {
        "system_prompt": "You are a fact-checker verifying claims via multi-hop evidence retrieval. Your goal is to find all supporting evidence by breaking down the claim into sub-questions and retrieving relevant passages.",
        "steps": [
            # Step 1: First-hop retrieval with deep search for better initial coverage
            {
                "number": 1,
                "title": "Retrieve first-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Filter and summarize first-hop evidence
            {
                "number": 2,
                "title": "Filter and summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract only the claim-relevant facts from the first-hop passages and create a concise summary.",
                "stage_action": (
                    "Review each retrieved passage. Keep only sentences directly relevant to verifying the claim. "
                    "Combine these into a short, coherent summary of evidence found in the first hop."
                ),
                "reasoning_questions": (
                    "Which sentences in the retrieved passages directly support or refute the claim? "
                    "What key entities and relationships are mentioned that are relevant to the claim?"
                ),
                "example_reasoning": (
                    "The claim is about climate change causing wildfires. Passage 1 mentions 'rising temperatures due to climate change have increased wildfire frequency in California'. "
                    "This is directly relevant. Passage 2 discusses unrelated economic data — ignore. "
                    "Summary: Climate change is linked to increased wildfire frequency in California."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (fixed dependency to preserve context)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing evidence and generate a precise search query for the second hop.",
                "stage_action": (
                    "Based on the filtered first-hop summary and the raw passages, determine what additional information is needed to verify the claim. "
                    "Write a concise search query to find this missing evidence.\n"
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific fact or detail is missing from the current evidence? "
                    "Which entities or relationships need further verification? "
                    "How can we phrase a query to get the missing information?"
                ),
                "example_reasoning": (
                    "Current evidence: Climate change increases wildfire frequency in California. "
                    "Missing: How much has the frequency increased? "
                    "Query: 'climate change wildfire frequency increase percentage California'"
                ),
                "dependencies": [1, 2],
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
            # Step 5: Unified evidence summary (first and second hop)
            {
                "number": 5,
                "title": "Create unified evidence summary (first and second hop)",
                "step_type": "llm",
                "aim": "Combine and filter evidence from both hops into a single coherent summary.",
                "stage_action": (
                    "Review the second-hop passages. Filter out irrelevant parts. Then, merge the relevant second-hop facts "
                    "with the first-hop summary to create a unified evidence summary covering all hops so far."
                ),
                "reasoning_questions": (
                    "Which parts of the second-hop passages are relevant? "
                    "How do they connect to the first-hop evidence? "
                    "What is the complete picture of evidence now?"
                ),
                "example_reasoning": (
                    "First-hop: Climate change increases wildfire frequency in California. "
                    "Second-hop: 'A 2020 study found a 300% increase in wildfire frequency in California since 1980 due to climate change.' "
                    "Unified: Climate change has caused a 300% increase in wildfire frequency in California since 1980."
                ),
                "dependencies": [2, 4],
            },
            # Step 6: Generate third-hop query with gap analysis
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Determine if a third hop is needed and generate a query for missing evidence.",
                "stage_action": (
                    "Based on the unified evidence summary, state whether the claim can be verified. "
                    "If not, write a concise search query for the missing evidence. "
                    "If no third hop is needed, output an empty string.\n"
                    "Provide ONLY the query (or empty string), no additional text."
                ),
                "reasoning_questions": (
                    "Is there any remaining gap in the evidence? "
                    "What specific fact would confirm or refute the claim? "
                    "If the evidence is complete, why is it sufficient?"
                ),
                "example_reasoning": (
                    "Unified evidence: Climate change has caused a 300% increase in wildfire frequency in California since 1980. "
                    "Missing: Is this increase solely due to climate change, or are there other factors? "
                    "Query: 'climate change sole cause of increased wildfire frequency California'"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval (deep)
            {
                "number": 7,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Updated unified evidence summary (including third hop)
            {
                "number": 8,
                "title": "Create updated unified evidence summary (including third hop)",
                "step_type": "llm",
                "aim": "Integrate third-hop evidence with existing summary to form a complete picture.",
                "stage_action": (
                    "Filter the third-hop passages for relevance and merge with the existing unified evidence summary "
                    "to create an updated summary."
                ),
                "reasoning_questions": (
                    "How does the third-hop evidence fill gaps or add new information? "
                    "Does it confirm, contradict, or add nuance to the existing summary? "
                    "What is the most current complete evidence?"
                ),
                "example_reasoning": (
                    "Existing: Climate change caused 300% increase in wildfires. "
                    "Third-hop: 'While climate change is a major factor, land management practices also contributed 20% to the increase.' "
                    "Updated: Climate change is the primary cause (80%) of the 300% increase in wildfire frequency in California since 1980, with land management contributing 20%."
                ),
                "dependencies": [5, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if a fourth hop is needed and generate a query for any remaining gaps.",
                "stage_action": (
                    "Based on the updated unified evidence summary, state whether the claim can be verified. "
                    "If not, write a concise search query for the missing evidence. "
                    "If no fourth hop is needed, output an empty string.\n"
                    "Provide ONLY the query (or empty string), no additional text."
                ),
                "reasoning_questions": (
                    "Are there any unresolved aspects of the claim? "
                    "What final piece of evidence would provide full verification? "
                    "If the evidence is complete, why is it sufficient?"
                ),
                "example_reasoning": (
                    "Updated evidence: Climate change is primary cause (80%) of the 300% increase. "
                    "Missing: What do scientific consensus and major studies say about the attribution? "
                    "Query: 'scientific consensus attribution of California wildfire frequency increase to climate change'"
                ),
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval (deep)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }