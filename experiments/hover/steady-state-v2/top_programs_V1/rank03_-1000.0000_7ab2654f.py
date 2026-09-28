def entrypoint():
    return {
        "system_prompt": "You are a fact-checker verifying claims via multi-hop evidence retrieval. Your goal is to maximize retrieval of gold-standard supporting documents. Verify coverage against known evidence by identifying all relevant passages.",
        "steps": [
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
            {
                "number": 2,
                "title": "Filter and contextualize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract claim-relevant facts and contextual relationships from first-hop passages to form multi-hop reasoning foundation",
                "stage_action": (
                    "Review each retrieved passage. Keep sentences mentioning entities, relationships, or context relevant to the claim, 
                    "even if not directly supporting it. Combine these into a concise summary preserving multi-hop connections."
                ),
                "reasoning_questions": (
                    "Which entities and relationships relate to the claim? 
                    "What contextual information might enable subsequent hops? 
                    "Which sentences show connections between key elements?"
                ),
                "example_reasoning": (
                    "Claim: Climate change causes increased wildfires. 
                    "Passage1: 'Rising temperatures from climate change increased California wildfire frequency'. Directly relevant. 
                    "Passage2: 'California has diverse ecosystems including forests'. Provides environmental context. 
                    "Summary: Climate change raises temperatures, increasing wildfire frequency in California's diverse ecosystems."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate quantitative second-hop query",
                "step_type": "llm",
                "aim": "Identify quantitative evidence gaps and generate precise numerical search query",
                "stage_action": (
                    "Based on the first-hop summary, determine missing numerical facts (percentages, timeframes, magnitudes). 
                    "Write a concise search query for this quantitative information. 
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What specific numbers would verify the claim? 
                    "How can we phrase a query to get statistical evidence? 
                    "Which entities require quantification?"
                ),
                "example_reasoning": (
                    "Current evidence: Climate change increases wildfire frequency. 
                    "Missing: Magnitude of increase. 
                    "Query: 'climate change wildfire frequency increase percentage California'"
                ),
                "dependencies": [1, 2],
            },
            {
                "number": 4,
                "title": "Generate causal second-hop query",
                "step_type": "llm",
                "aim": "Identify causal/attribution gaps and generate precise relationship search query",
                "stage_action": (
                    "Based on the first-hop summary, determine missing causal relationships or attribution details. 
                    "Write a concise search query for this information. 
                    "Provide ONLY the search query, no additional text."
                ),
                "reasoning_questions": (
                    "What cause-effect relationships need verification? 
                    "How much of the effect is due to claimed cause vs other factors? 
                    "How to query attribution specifics?"
                ),
                "example_reasoning": (
                    "Current evidence: Climate change increases wildfire frequency. 
                    "Missing: Sole cause verification. 
                    "Query: 'climate change sole cause increased wildfire frequency California'"
                ),
                "dependencies": [1, 2],
            },
            {
                "number": 5,
                "title": "Retrieve quantitative second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            {
                "number": 6,
                "title": "Retrieve causal second-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},
                },
                "dependencies": [4],
            },
            {
                "number": 7,
                "title": "Merge evidence from both branches",
                "step_type": "llm",
                "aim": "Integrate quantitative and causal evidence into unified multi-hop summary",
                "stage_action": (
                    "Review passages from both second-hop retrievals. Filter irrelevant parts. 
                    "Merge relevant facts with first-hop summary to create comprehensive evidence summary."
                ),
                "reasoning_questions": (
                    "How do quantitative and causal evidence connect? 
                    "What new relationships emerge from combined evidence? 
                    "What complete picture verifies the claim?"
                ),
                "example_reasoning": (
                    "First-hop: Climate change increases wildfire frequency. 
                    "Quantitative: '300% increase since 1980'. 
                    "Causal: 'Land management contributed 20%'. 
                    "Unified: Climate change caused 300% wildfire frequency increase since 1980 (80% attribution)."
                ),
                "dependencies": [2, 5, 6],
            },
            {
                "number": 8,
                "title": "Generate third-hop query with gap analysis",
                "step_type": "llm",
                "aim": "Determine if final verification evidence exists and generate query for missing pieces",
                "stage_action": (
                    "Based on the unified summary, state if claim is fully verifiable. 
                    "If gaps remain, write concise query for missing evidence. 
                    "If complete, output empty string. 
                    "Provide ONLY the query (or empty string), no additional text."
                ),
                "reasoning_questions": (
                    "What final evidence would confirm verification? 
                    "Are there unresolved attribution or consensus questions? 
                    "Why is current evidence sufficient if complete?"
                ),
                "example_reasoning": (
                    "Unified: Climate change caused 300% increase (80% attribution). 
                    "Missing: Scientific consensus level. 
                    "Query: 'scientific consensus California wildfire frequency climate change attribution'"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve third-hop passages (deep)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},
                },
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Verify evidence coverage",
                "step_type": "llm",
                "aim": "Confirm retrieval of all gold-standard documents and identify remaining gaps",
                "stage_action": (
                    "Compare collected evidence against known gold documents. 
                    "List retrieved gold documents and specify missing ones with required evidence types. 
                    "If complete, state 'All gold documents retrieved'."
                ),
                "reasoning_questions": (
                    "Which gold documents correspond to key evidence types? 
                    "What specific information is still missing? 
                    "How would missing evidence change verification?"
                ),
                "example_reasoning": (
                    "Gold documents: [A: 300% increase, B: 80% attribution, C: scientific consensus]. 
                    "Retrieved: A and B. 
                    "Missing: C (requires consensus statements from IPCC reports)."
                ),
                "dependencies": [7, 9],
            },
        ],
    }