def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Always be precise and focused. When generating search queries, aim for clarity and relevance to the missing evidence. When summarizing, extract only the most relevant facts for verifying the claim.",
        "steps": [
            # Step 1: First-hop retrieval (deepened for better recall)
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
            # Step 2: Summarize first-hop evidence with focused questions
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from first-hop passages directly relevant to claim verification.",
                "stage_action": (
                    "Read the retrieved passages and identify facts that support/refute the claim. "
                    "Produce a concise summary of only these facts. Exclude irrelevant information."
                ),
                "reasoning_questions": "What specific facts directly support or refute the claim? What critical information is still missing?",
                "example_reasoning": (
                    "Example:\nClaim: 'The Eiffel Tower was completed in 1887.'\n"
                    "Retrieved passages: [1] Eiffel Tower | The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It is named after the engineer Gustave Eiffel, whose company designed and built the tower.\n"
                    "Summary: The Eiffel Tower is a famous tower in Paris designed by Gustave Eiffel. Missing information: The completion year."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate two independent queries for parallel evidence paths (JSON format)
            {
                "number": 3,
                "title": "Generate dual second-hop queries",
                "step_type": "llm",
                "aim": "Identify two independent evidence gaps and generate distinct search queries for parallel retrieval.",
                "stage_action": (
                    "Based on the claim and first-hop summary, determine two separate missing information aspects. "
                    "Formulate two search queries targeting each gap. Output ONLY in JSON format: "
                    "{\"query1\": \"first query\", \"query2\": \"second query\"}"
                ),
                "reasoning_questions": "What are two distinct claim aspects lacking evidence? How can each be phrased as a precise search query?",
                "example_reasoning": (
                    "Example:\nClaim: 'The Eiffel Tower was completed in 1887.'\n"
                    "First-hop evidence summary: 'The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It is named after the engineer Gustave Eiffel, whose company designed and built the tower.'\n"
                    "Missing information: (1) The start year of construction, (2) The completion year.\n"
                    "Output: {\"query1\": \"Eiffel Tower construction start year\", \"query2\": \"Eiffel Tower completion year\"}"
                ),
                "dependencies": [2],
            },
            # Step 4: Extract first query from JSON
            {
                "number": 4,
                "title": "Extract first query",
                "step_type": "llm",
                "aim": "Isolate the first search query from JSON output.",
                "stage_action": (
                    "Read the JSON output from step3 and extract the value of the 'query1' field. "
                    "Output ONLY the query string without any additional formatting or text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example:\nInput: '{\"query1\": \"Eiffel Tower construction start year\", \"query2\": \"Eiffel Tower completion year\"}'\n"
                    "Output: 'Eiffel Tower construction start year'"
                ),
                "dependencies": [3],
            },
            # Step 5: Extract second query from JSON
            {
                "number": 5,
                "title": "Extract second query",
                "step_type": "llm",
                "aim": "Isolate the second search query from JSON output.",
                "stage_action": (
                    "Read the JSON output from step3 and extract the value of the 'query2' field. "
                    "Output ONLY the query string without any additional formatting or text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": (
                    "Example:\nInput: '{\"query1\": \"Eiffel Tower construction start year\", \"query2\": \"Eiffel Tower completion year\"}'\n"
                    "Output: 'Eiffel Tower completion year'"
                ),
                "dependencies": [3],
            },
            # Step 6: First parallel second-hop retrieval
            {
                "number": 6,
                "title": "Retrieve first branch passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},  # Step4 output (index 3)
                },
                "dependencies": [4],
            },
            # Step 7: Second parallel second-hop retrieval
            {
                "number": 7,
                "title": "Retrieve second branch passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},  # Step5 output (index 4)
                },
                "dependencies": [5],
            },
            # Step 8: Merge and summarize parallel second-hop evidence
            {
                "number": 8,
                "title": "Summarize merged second-hop evidence",
                "step_type": "llm",
                "aim": "Consolidate key facts from both second-hop retrievals for claim verification.",
                "stage_action": (
                    "Read passages from both second-hop retrievals and identify critical facts supporting/refuting the claim. "
                    "Produce a single concise summary. Exclude irrelevant information and resolve contradictions if present."
                ),
                "reasoning_questions": "What facts directly address the original gaps? How do both evidence sets collectively verify the claim?",
                "example_reasoning": (
                    "Example:\nClaim: 'The Eiffel Tower was completed in 1887.'\n"
                    "Step6 passages: [1] Construction began in 1887. ...\n"
                    "Step7 passages: [1] Completion occurred in March 1889. ...\n"
                    "Summary: Construction of the Eiffel Tower began in 1887 and was completed in 1889."
                ),
                "dependencies": [6, 7],
            },
            # Step 9: Adaptive termination check after second hops
            {
                "number": 9,
                "title": "Check evidence completeness",
                "step_type": "llm",
                "aim": "Determine if evidence suffices for verification or if third hop is needed.",
                "stage_action": (
                    "Review first-hop summary (step2) and merged second-hop summary (step8). "
                    "If claim can be verified, output 'TERMINATE'. Otherwise, formulate a highly specific third query. "
                    "Output ONLY 'TERMINATE' or the query string."
                ),
                "reasoning_questions": "What exact fact is still missing? Is current evidence unambiguous?",
                "example_reasoning": (
                    "Example 1 (terminate):\nClaim: 'The Eiffel Tower was completed in 1887.'\n"
                    "First-hop: 'The Eiffel Tower is a famous tower in Paris designed by Gustave Eiffel.'\n"
                    "Second-hop: 'Construction began in 1887 and completed in 1889.'\n"
                    "Decision: Evidence shows completion in 1889 (contradicts claim). Output: 'TERMINATE'\n\n"
                    "Example 2 (continue):\nClaim: 'The Eiffel Tower was completed in 1887.'\n"
                    "First-hop: 'The Eiffel Tower is a famous tower in Paris designed by Gustave Eiffel.'\n"
                    "Second-hop: 'Construction began in 1887.' and 'The tower was completed after two years.'\n"
                    "Missing: Exact completion year. Query: 'Eiffel Tower completion year 1887 1889'"
                ),
                "dependencies": [2, 8],
            },
            # Step 10: Third-hop retrieval with deep recall
            {
                "number": 10,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",  # Changed from 'retrieve' to 'retrieve_deep'
                    "input_mapping": {"query": "$history[8]"},  # Step9 output (index 8)
                },
                "dependencies": [9],
            },
        ],
    }