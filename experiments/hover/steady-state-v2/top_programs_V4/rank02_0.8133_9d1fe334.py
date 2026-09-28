def entrypoint():
    return {
        "system_prompt": (
            "You are an expert fact-checker assistant. Your task is to verify claims by retrieving relevant evidence from Wikipedia. "
            "Follow these principles:\n"
            "- Always base your reasoning on the retrieved passages and the original claim.\n"
            "- For query generation steps, output ONLY the search query without any additional text.\n"
            "- For summarization steps, output ONLY key facts without any additional reasoning or text.\n"
            "- In gap analysis, be thorough: if any part of the claim remains unverified, generate a query to find the missing evidence."
        ),
        "steps": [
            # Step 1: First-hop retrieval (deep)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop with concrete gap example
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from first-hop passages and identify unverified aspects.",
                "stage_action": (
                    "Read retrieved passages and identify facts directly relevant to verifying the claim. "
                    "Output ONLY key facts without reasoning. Then state the specific unverified claim aspect (gap)."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified based on current evidence?",
                "example_reasoning": (
                    "Example:\n"
                    "  Claim: 'Marie Curie won two Nobel Prizes'\n"
                    "  Retrieved passages: [0] Marie Curie | won the Nobel Prize in Physics in 1903.\n"
                    "  Gap: 'Evidence only shows one Nobel Prize; missing the second (Chemistry, 1911). Therefore, next query should target Chemistry prize.'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for second-hop branch A
            {
                "number": 3,
                "title": "Generate second-hop query A",
                "step_type": "llm",
                "aim": "Identify one specific unverified aspect from first summary for investigation.",
                "stage_action": (
                    "Based on the gap in first-hop summary, formulate a concise search query for one unverified aspect. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: For claim 'Einstein was born in Germany', if evidence mentions Ulm but not country, output: 'Ulm location'",
                "dependencies": [2],
            },
            # Step 4: Generate query for second-hop branch B
            {
                "number": 4,
                "title": "Generate second-hop query B",
                "step_type": "llm",
                "aim": "Identify another distinct unverified aspect from first summary for investigation.",
                "stage_action": (
                    "Based on the gap in first-hop summary, formulate a different concise search query for another unverified aspect. "
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: For claim 'Einstein was born in Germany', if evidence mentions Ulm but not country, output: 'Einstein birthplace country'",
                "dependencies": [2],
            },
            # Step 5: Second-hop retrieval A (deep)
            {
                "number": 5,
                "title": "Retrieve second-hop passages A",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 6: Second-hop retrieval B (deep)
            {
                "number": 6,
                "title": "Retrieve second-hop passages B",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            # Step 7: Merge second-hop results with concrete gap example
            {
                "number": 7,
                "title": "Merge second-hop evidence",
                "step_type": "llm",
                "aim": "Integrate evidence from both branches and identify remaining gaps.",
                "stage_action": (
                    "Read passages from both second-hop branches. Output ONLY key facts without reasoning. "
                    "Then state the specific unverified claim aspect (gap)."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified after both branches?",
                "example_reasoning": (
                    "Example 1 (gap exists):\n"
                    "  Claim: 'The Eiffel Tower was built in 1889'\n"
                    "  Evidence A: [0] Eiffel Tower | construction began in 1887.\n"
                    "  Evidence B: [0] Eiffel Tower | completed in March 1889.\n"
                    "  Gap: 'Architect is not mentioned.'\n\n"
                    "Example 2 (no gap):\n"
                    "  Claim: 'The Eiffel Tower was built in 1889'\n"
                    "  Evidence A: [0] Eiffel Tower | construction began in 1887 and completed in 1889.\n"
                    "  Evidence B: [0] Eiffel Tower | designed by Gustave Eiffel.\n"
                    "  Gap: 'All aspects verified.'"
                ),
                "dependencies": [5, 6],
            },
            # Step 8: Conditionally generate third-hop query
            {
                "number": 8,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate query for third hop only if gap exists.",
                "stage_action": (
                    "Review gap from second-hop summary. If unverified aspect exists, formulate concise search query. "
                    "If claim is fully verified, output 'no_query'. Provide ONLY query or 'no_query', no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example 1 (gap exists):\n"
                    "  Claim: 'The Eiffel Tower was built in 1889'\n"
                    "  Evidence: [shows construction dates but not architect]\n"
                    "  Output: 'Eiffel Tower architect'\n\n"
                    "Example 2 (no gap):\n"
                    "  Claim: 'The Eiffel Tower was built in 1889'\n"
                    "  Evidence: [shows construction dates and architect]\n"
                    "  Output: 'no_query'"
                ),
                "dependencies": [7],
            },
            # Step 9: Third-hop retrieval (deep)
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
        ],
    }