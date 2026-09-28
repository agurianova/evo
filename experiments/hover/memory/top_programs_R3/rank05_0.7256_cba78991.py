def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims using Wikipedia evidence. At each step:\n- For query generation: Output ONLY the search query string or 'NO_QUERY_NEEDED'\n- For summaries: Be concise, focusing only on claim-relevant facts\n- Never add explanations or formatting in query steps",
        "steps": [
            # Step 1: First-hop retrieval
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key claim-relevant facts from initial evidence",
                "stage_action": "Read retrieved passages and summarize ONLY facts directly relevant to verifying the claim. Omit irrelevant details.",
                "reasoning_questions": "1. Which facts directly support/refute the claim?\n2. What specific data points are most critical?\n3. Are there contradictions in this evidence?",
                "example_reasoning": "Claim: 'Tokyo's 2023 population is 14.2 million'\nPassages: 'Tokyo population 13.5M (2019)'\nRelevant fact: 2019 population data exists but 2023 data missing",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify precise missing information and generate search query",
                "stage_action": "Based on the first-hop summary, determine the exact missing information needed. Output ONLY the search query string with no additional text.",
                "reasoning_questions": "1. What specific fact is missing to verify the claim?\n2. What is the most precise search string for this fact?",
                "example_reasoning": "First-hop: 'Tokyo population 13.5M (2019)'\nMissing: 2023 population data\nTokyo population 2023",
                "dependencies": [2],
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
            # Step 5: Summarize second-hop evidence (NEW)
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Distill second-hop passages into claim-relevant facts",
                "stage_action": "Read retrieved passages and extract ONLY facts that directly address the claim's verification needs. Be concise.",
                "reasoning_questions": "1. What new facts does this evidence provide?\n2. How do they connect to the first-hop evidence?\n3. What gaps remain?",
                "example_reasoning": "Claim: 'Tokyo 2023 population 14.2M'\nPassages: '2023 census: Tokyo population 14.2 million'\nRelevant fact: 2023 population confirmed as 14.2 million",
                "dependencies": [4],
            },
            # Step 6: Integrate evidence & generate third-hop query
            {
                "number": 6,
                "title": "Integrate evidence and generate query",
                "step_type": "llm",
                "aim": "Determine verification status and conditionally generate query",
                "stage_action": "Combine both evidence summaries. If verification is complete, output 'NO_QUERY_NEEDED'. Otherwise, output ONLY the search query for missing evidence.",
                "reasoning_questions": "1. Is the claim fully verified by current evidence?\n2. If not, what specific fact is missing?\n3. What is the optimal query for this fact?",
                "example_reasoning": "Scenario A (sufficient):\nFirst: 'Tokyo pop 13.5M (2019)'\nSecond: 'Tokyo pop 14.2M (2023)'\nClaim matches second evidence\nNO_QUERY_NEEDED\n\nScenario B (insufficient):\nFirst: 'Tokyo pop 13.5M (2019)'\nSecond: 'Tokyo pop 14.2M (2023)'\nMissing: population density\nTokyo population density 2023",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
        ],
    }