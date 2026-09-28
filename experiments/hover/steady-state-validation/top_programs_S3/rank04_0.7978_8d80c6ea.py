def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving and analyzing evidence from Wikipedia.\nBe precise and concise in your outputs. For query generation steps, output ONLY the search query string or nothing (e.g., do not output: 'Query: ...', just the raw query).\nFor evidence summary steps: if no passages were retrieved, output exactly 'SKIPPED'. Otherwise, output a concise paragraph of key facts AND explicitly state any remaining gaps that prevent verification.\nExamples of bad outputs in query generation steps:\n  - DO NOT output: 'Here is the query: ...'\n  - DO NOT output: 'Query: Eiffel Tower construction start year'\n  - Correct: 'Eiffel Tower construction start year'",
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
                "stage_action": "Read all retrieved passages. If no passages were retrieved, output exactly 'SKIPPED'. Otherwise, identify facts relevant to verifying the claim and summarize them concisely.",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed and generate next search query",
                "stage_action": "Based on the evidence summary, determine if the claim can be verified. If yes, output nothing. If not, output a concise search query for missing evidence. Output ONLY the query string or nothing.",
                "reasoning_questions": "What key entities or relations are missing to verify the claim? What specific information would bridge the gap between the claim and current evidence? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": "Example 1 (entity gap):\nClaim: 'The Eiffel Tower was built in 1887.'\nFirst-hop evidence: 'The Eiffel Tower was completed in 1889.'\nMissing: exact construction start date.\nQuery: 'Eiffel Tower construction start year'\n\nExample 2 (temporal gap):\nClaim: 'World War II ended in 1945.'\nFirst-hop evidence: 'World War II involved many countries.'\nMissing: end year of WWII.\nQuery: 'World War II end year'\n\nExample 3 (causal gap):\nClaim: 'Smoking causes lung cancer.'\nFirst-hop evidence: 'Lung cancer is a disease.'\nMissing: causal link between smoking and lung cancer.\nQuery: 'smoking lung cancer causation'",
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
                "stage_action": "Read all retrieved passages. If no passages were retrieved (because query was empty), output exactly 'SKIPPED'. Otherwise, identify facts relevant to verifying the claim and summarize them concisely.",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries",
                "stage_action": "Consider the first-hop evidence summary and second-hop evidence summary. If second-hop summary is 'SKIPPED', treat it as not performed. Determine if claim can be verified with available evidence. If yes, output nothing. If not, output concise search query. Output ONLY the query string or nothing.",
                "reasoning_questions": "What critical gaps remain after reviewing all evidence? What specific query would target the missing verification element? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": "Example 1 (entity gap):\nFirst-hop: 'Eiffel Tower completed 1889' | Second-hop: 'SKIPPED'\nMissing: construction duration.\nQuery: 'Eiffel Tower construction period'\n\nExample 2 (temporal gap):\nFirst-hop: 'World War II started in 1939' | Second-hop: 'World War II major battles'\nMissing: end year.\nQuery: 'World War II end date'\n\nExample 3 (causal gap):\nFirst-hop: 'Lung cancer symptoms' | Second-hop: 'Smoking health effects'\nMissing: direct causation evidence.\nQuery: 'smoking as cause of lung cancer'",
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
                "stage_action": "Read all retrieved passages. If no passages were retrieved, output exactly 'SKIPPED'. Otherwise, identify facts relevant to verifying the claim and summarize them concisely.",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries and generate next search query",
                "stage_action": "Consider the first-hop, second-hop, and third-hop evidence summaries (skip any marked 'SKIPPED'). Determine if the claim can be verified. If yes, output nothing. If not, output a concise search query for missing evidence. Output ONLY the query string or nothing.",
                "reasoning_questions": "What critical gaps remain after reviewing all evidence? What specific query would target the missing verification element? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": "Example 1 (entity gap):\nFirst-hop: 'Eiffel Tower completed 1889' | Second-hop: 'Eiffel Tower height' | Third-hop: 'Eiffel Tower designer'\nMissing: construction start date.\nQuery: 'Eiffel Tower construction start year'\n\nExample 2 (temporal gap):\nFirst-hop: 'World War II started 1939' | Second-hop: 'World War II major events' | Third-hop: 'D-Day 1944'\nMissing: end year.\nQuery: 'World War II end year'\n\nExample 3 (causal gap):\nFirst-hop: 'Lung cancer symptoms' | Second-hop: 'Smoking health effects' | Third-hop: 'Carcinogens in tobacco'\nMissing: epidemiological evidence.\nQuery: 'smoking lung cancer epidemiology'",
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
