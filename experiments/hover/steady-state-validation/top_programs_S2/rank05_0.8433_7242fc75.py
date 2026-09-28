def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker focused on maximizing evidence recall. Prioritize thorough exploration: identify all gaps and generate precise queries. Always output queries in the exact required format.",
        "steps": [
            # Step 1: First-hop retrieval with high recall
            {
                "number": 1,
                "title": "Retrieve first-hop passages (broad)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop and identify 0-3 gaps
            {
                "number": 2,
                "title": "Summarize first-hop evidence and identify dynamic gaps",
                "step_type": "llm",
                "aim": "Extract key facts from first-hop passages and identify 0-3 distinct gaps for second hop.",
                "stage_action": (
                    "Read the retrieved passages and identify facts relevant to the claim. "
                    "Summarize the most important evidence in one paragraph. Then, list 0 to 3 distinct missing pieces of information critical for verification. "
                    "Format:\nEvidence Summary: ...\nGap 1: ...\nGap 2: ... (if exists)\nGap 3: ... (if exists)"
                ),
                "reasoning_questions": (
                    "What are the key entities and relationships mentioned in the claim? "
                    "What specific facts are provided by the retrieved passages? "
                    "How many distinct critical gaps (0-3) remain to confirm or refute the claim? (Be specific and distinct.)"
                ),
                "example_reasoning": (
                    "Example 0 (0 gaps): \nClaim: 'Person A holds Position B at Organization C.' \n"
                    "Retrieved passages: 'Person A holds Position B at Organization C.' \n"
                    "Evidence Summary: Person A holds Position B at Organization C. \n\n"
                    "Example 1 (1 gap): \nClaim: 'Person A holds Position B at Organization C.' \n"
                    "Retrieved passages: 'Person A is associated with Organization C.' \n"
                    "Evidence Summary: Person A is associated with Organization C. \n"
                    "Gap 1: Confirmation that Person A holds Position B at Organization C.\n\n"
                    "Example 2 (2 gaps): \nClaim: 'Person A holds Position B at Organization C and received Award D in Year E.' \n"
                    "Retrieved passages: 'Person A is associated with Organization C.' and 'Award D was given in Year E.' \n"
                    "Evidence Summary: Person A is associated with Organization C; Award D was given in Year E. \n"
                    "Gap 1: Confirmation that Person A holds Position B at Organization C. \n"
                    "Gap 2: Confirmation that Person A received Award D (specifically).\n\n"
                    "Example 3 (3 gaps): \nClaim: 'Person A holds Position B at Organization C, received Award D in Year E, and founded Company F in Year G.' \n"
                    "Retrieved passages: 'Person A is associated with Organization C.' and 'Award D was given in Year E.' \n"
                    "Evidence Summary: Person A is associated with Organization C; Award D was given in Year E. \n"
                    "Gap 1: Confirmation that Person A holds Position B at Organization C. \n"
                    "Gap 2: Confirmation that Person A received Award D. \n"
                    "Gap 3: Confirmation that Person A founded Company F in Year G."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate query for gap 1 (if exists)
            {
                "number": 3,
                "title": "Generate second-hop query for gap 1",
                "step_type": "llm",
                "aim": "Generate search query for Gap 1 from step 2 if it exists.",
                "stage_action": (
                    "Based on Gap 1 from step 2, write a concise search query optimized for BM25. "
                    "If step 2 did not list Gap 1 (i.e., 0 gaps), output 'NO_GAPS'. "
                    "Provide ONLY the query string or 'NO_GAPS', no additional text."
                ),
                "reasoning_questions": (
                    "Is Gap 1 provided in step 2? If yes, what key entities and attributes are central to it? "
                    "How can we phrase a query that precisely targets the missing information without being too broad?"
                ),
                "example_reasoning": (
                    "Example Gap 1: 'Confirmation that Person A holds Position B at Organization C'\n"
                    "Query: 'Person A Position B Organization C confirmation'\n\n"
                    "Example with no Gap 1: \nStep 2 output: Evidence Summary: ...\n(no gaps)\n\n"
                    "Output: 'NO_GAPS'"
                ),
                "dependencies": [2],
            },
            # Step 4: Generate query for gap 2 (if exists)
            {
                "number": 4,
                "title": "Generate second-hop query for gap 2",
                "step_type": "llm",
                "aim": "Generate search query for Gap 2 from step 2 if it exists.",
                "stage_action": (
                    "Based on Gap 2 from step 2, write a concise search query optimized for BM25. "
                    "If step 2 did not list Gap 2 (i.e., fewer than 2 gaps), output 'NO_GAPS'. "
                    "Provide ONLY the query string or 'NO_GAPS', no additional text."
                ),
                "reasoning_questions": (
                    "Is Gap 2 provided in step 2? If yes, what key entities and attributes are central to it? "
                    "How can we phrase a precise query for the missing information?"
                ),
                "example_reasoning": (
                    "Example Gap 2: 'Confirmation that Person A received Award D'\n"
                    "Query: 'Person A Award D recipient Year E'\n\n"
                    "Example with no Gap 2: \nStep 2 output: Evidence Summary: ...\nGap 1: ...\n(no Gap 2)\n\n"
                    "Output: 'NO_GAPS'"
                ),
                "dependencies": [2],
            },
            # Step 5: Generate query for gap 3 (if exists)
            {
                "number": 5,
                "title": "Generate second-hop query for gap 3",
                "step_type": "llm",
                "aim": "Generate search query for Gap 3 from step 2 if it exists.",
                "stage_action": (
                    "Based on Gap 3 from step 2, write a concise search query optimized for BM25. "
                    "If step 2 did not list Gap 3 (i.e., fewer than 3 gaps), output 'NO_GAPS'. "
                    "Provide ONLY the query string or 'NO_GAPS', no additional text."
                ),
                "reasoning_questions": (
                    "Is Gap 3 provided in step 2? If yes, what key entities and attributes are central to it? "
                    "How can we phrase a precise query for the missing information?"
                ),
                "example_reasoning": (
                    "Example Gap 3: 'Confirmation that Person A founded Company F in Year G'\n"
                    "Query: 'Person A founded Company F Year G'\n\n"
                    "Example with no Gap 3: \nStep 2 output: Evidence Summary: ...\nGap 1: ...\nGap 2: ...\n(no Gap 3)\n\n"
                    "Output: 'NO_GAPS'"
                ),
                "dependencies": [2],
            },
            # Step 6: Second-hop retrieval branch 1
            {
                "number": 6,
                "title": "Retrieve second-hop passages (branch 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},  # Step 3 output
                },
                "dependencies": [3],
            },
            # Step 7: Second-hop retrieval branch 2
            {
                "number": 7,
                "title": "Retrieve second-hop passages (branch 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},  # Step 4 output
                },
                "dependencies": [4],
            },
            # Step 8: Second-hop retrieval branch 3
            {
                "number": 8,
                "title": "Retrieve second-hop passages (branch 3)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[4]"},  # Step 5 output
                },
                "dependencies": [5],
            },
            # Step 9: Consolidate evidence and generate critical compound query
            {
                "number": 9,
                "title": "Consolidate evidence and generate compound query",
                "step_type": "llm",
                "aim": "Consolidate evidence from active second-hop branches, identify top 1-2 critical gaps, and generate compound query.",
                "stage_action": (
                    "Read the retrieved passages from step 6, 7, and 8, but note: only the first n branches are relevant (n = number of gaps identified in step 2, by counting 'Gap 1:', 'Gap 2:', etc. lines). "
                    "Compare evidence across these branches. Note overlaps and focus on unique information. "
                    "Based on the Evidence Summary from step 2 and new evidence, determine the top 1-2 most critical missing pieces for verification. "
                    "Generate a concise BM25-optimized query that combines key terms from these gaps. "
                    "Output EXACTLY in format:\nConsolidated Evidence: ...\nCritical Gaps: ...\nQuery: ...\n"
                    "Provide ONLY this format, no additional text."
                ),
                "reasoning_questions": (
                    "What new evidence was found in each active branch (step6, step7, step8)? "
                    "Is there overlap between branches? "
                    "Given all evidence, what are the top 1-2 most critical missing pieces for verification? "
                    "How can we phrase a precise compound query covering these gaps?"
                ),
                "example_reasoning": (
                    "Example (1 gap): \nClaim: 'Entity X has property Y and relationship Z with Entity W'. \n"
                    "Step2 Evidence Summary: Entity X has property Y; relationship Z not mentioned. \n"
                    "Step2 Gaps: Gap1: Confirmation of relationship Z with Entity W.\n"
                    "Step6 passages: 'Entity X has relationship Z with Entity W.' \n"
                    "Analysis: Branch1 confirms relationship Z with Entity W. \n"
                    "Consolidated Evidence: Entity X has property Y and relationship Z with Entity W. \n"
                    "Critical Gaps: None.\n"
                    "Query: N/A\n\n"
                    "Example (2 gaps): \nClaim: 'Person A holds Position B at Organization C and received Award D in Year E.' \n"
                    "Step2 Evidence Summary: Person A is associated with Organization C; Award D was given in Year E. \n"
                    "Step2 Gaps: Gap1: Confirmation of Position B; Gap2: Confirmation that Person A received Award D.\n"
                    "Step6 passages (Gap1): 'Person A is the CEO of Organization C.' \n"
                    "Step7 passages (Gap2): 'Person A was awarded Award D in Year E.' \n"
                    "Analysis: Step6 confirms Position B (CEO) but claim specifies Position B; Step7 confirms Award D but not recipient. \n"
                    "Consolidated Evidence: Person A is the CEO of Organization C; Person A was awarded Award D in Year E. \n"
                    "Critical Gaps: 1. Confirmation that CEO is Position B; 2. Confirmation that Person A is the specific recipient of Award D.\n"
                    "Query: 'Person A Position B CEO Organization C Award D recipient confirmation'"
                ),
                "dependencies": [2, 6, 7, 8],
            },
            # Step 10: Third-hop retrieval
            {
                "number": 10,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {
                        "query": "$history[8]"
                    },  # Step 9 output (Query line)
                },
                "dependencies": [9],
            },
        ],
    }
