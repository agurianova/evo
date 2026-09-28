def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving and analyzing evidence from Wikipedia.\nBe precise and concise in your outputs. For query generation steps, output ONLY the search query string or nothing. DO NOT output any explanatory text, prefixes, or suffixes.\nFor evidence summary steps: if no passages were retrieved, output exactly 'SKIPPED'. Otherwise, output a concise paragraph of key facts and explicitly state gaps using 'Gaps: [description]'.",
        "steps": [
            # Step 1: First-hop retrieval (deep search)
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
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from first-hop passages or indicate if none found",
                "stage_action": "Read all retrieved passages. If no passages were retrieved, output exactly 'SKIPPED'. Otherwise, identify facts relevant to verifying the claim and summarize them concisely. Then, explicitly state any gaps in the evidence using the format: 'Gaps: [gap description]'.",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed and generate next search query",
                "stage_action": "Based on the evidence summary, determine if the claim can be verified. If yes, output nothing. If not, output a concise search query for missing evidence. Output ONLY the query string or nothing.",
                "reasoning_questions": "What key entities or relations are missing to verify the claim? What specific information would bridge the gap between the claim and current evidence?",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1887.' -> First-hop evidence: 'The Eiffel Tower was completed in 1889.' -> Missing: exact construction start date (temporal gap). Query: 'Eiffel Tower construction start year'\nClaim: 'Albert Einstein won the Nobel Prize for his theory of relativity.' -> First-hop evidence: 'Albert Einstein won the Nobel Prize in Physics in 1921.' -> Missing: specific work for which he won (entity gap). Query: 'Albert Einstein Nobel Prize reason'\nClaim: 'The Great Depression was caused by the stock market crash of 1929.' -> First-hop evidence: 'The stock market crash of 1929 marked the beginning of the Great Depression.' -> Missing: causal link between crash and depression (causal gap). Query: 'How did the 1929 stock market crash cause the Great Depression?'",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (deep search)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from second-hop passages or indicate if skipped",
                "stage_action": "Read all retrieved passages. If no passages were retrieved (because query was empty), output exactly 'SKIPPED'. Otherwise, identify facts relevant to verifying the claim and summarize them concisely. Then, explicitly state any gaps in the evidence using the format: 'Gaps: [gap description]'.",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries",
                "stage_action": "Consider the first-hop evidence summary and second-hop evidence summary. If second-hop summary is 'SKIPPED', treat it as not performed. Determine if claim can be verified with available evidence. If yes, output nothing. If not, output concise search query. Output ONLY the query string or nothing.",
                "reasoning_questions": "What critical gaps remain after reviewing all evidence? What specific query would target the missing verification element? Categorize the gap as entity, temporal, or causal to guide query formulation.",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1887.' -> First-hop evidence: 'The Eiffel Tower was completed in 1889.' -> Missing: exact construction start date (temporal gap). Query: 'Eiffel Tower construction start year'\nClaim: 'Albert Einstein won the Nobel Prize for his theory of relativity.' -> First-hop evidence: 'Albert Einstein won the Nobel Prize in Physics in 1921.' -> Missing: specific work for which he won (entity gap). Query: 'Albert Einstein Nobel Prize reason'\nClaim: 'The Great Depression was caused by the stock market crash of 1929.' -> First-hop evidence: 'The stock market crash of 1929 marked the beginning of the Great Depression.' -> Missing: causal link between crash and depression (causal gap). Query: 'How did the 1929 stock market crash cause the Great Depression?'",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval (deep search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Summarize third-hop evidence
            {
                "number": 8,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from third-hop passages or indicate if skipped",
                "stage_action": "Read all retrieved passages. If no passages were retrieved, output exactly 'SKIPPED'. Otherwise, identify facts relevant to verifying the claim and summarize them concisely. Then, explicitly state any gaps in the evidence using the format: 'Gaps: [gap description]'.",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries and generate next search query",
                "stage_action": "Consider all evidence summaries (skip any marked 'SKIPPED'). Determine if the claim can be verified. If yes, output nothing. If not, output a concise search query for missing evidence. Output ONLY the query string or nothing.",
                "reasoning_questions": "What critical gaps remain after reviewing all evidence? What specific query would target the missing verification element? Categorize the gap as entity, temporal, or causal to guide query formulation.",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1887.' -> First-hop evidence: 'The Eiffel Tower was completed in 1889.' -> Missing: exact construction start date (temporal gap). Query: 'Eiffel Tower construction start year'\nClaim: 'Albert Einstein won the Nobel Prize for his theory of relativity.' -> First-hop evidence: 'Albert Einstein won the Nobel Prize in Physics in 1921.' -> Missing: specific work for which he won (entity gap). Query: 'Albert Einstein Nobel Prize reason'\nClaim: 'The Great Depression was caused by the stock market crash of 1929.' -> First-hop evidence: 'The stock market crash of 1929 marked the beginning of the Great Depression.' -> Missing: causal link between crash and depression (causal gap). Query: 'How did the 1929 stock market crash cause the Great Depression?'",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval (deep search)
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }
