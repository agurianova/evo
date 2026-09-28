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
                "reasoning_questions": "What key entities, dates, or relations are present in the passages? What specific information from the claim remains unverified?",
                "example_reasoning": "Example:\nClaim: 'The Eiffel Tower was built in 1887.'\nPassages:\n[1] Eiffel Tower | Completed in 1889.\n[2] Gustave Eiffel | Designed the Eiffel Tower.\nSummary: The Eiffel Tower was completed in 1889 and designed by Gustave Eiffel. However, the construction start year is missing, which is needed to verify the claim of 1887.",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed and generate next search query",
                "stage_action": "Break down the claim into key components. For each component, list the evidence found so far (if any) and what is still missing. If all components are verified, output nothing. Otherwise, output a concise search query for the most critical missing piece. Output ONLY the query string or nothing.",
                "reasoning_questions": "What are the key components of the claim (e.g., entities, dates, relations)? For each component, what evidence have we found? What evidence is still missing? Which missing piece is most critical for verification? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": "Example 1 (entity gap):\nClaim: 'The Eiffel Tower was built in 1887.'\nFirst-hop evidence: 'The Eiffel Tower was completed in 1889.'\nComponent breakdown:\n- Entity: Eiffel Tower -> verified as existing\n- Construction start year: missing (only completion year 1889 found)\n- Claimed start year: 1887 -> not verified\nCritical gap: construction start year\nQuery: 'Eiffel Tower construction start year'\n\nExample 2 (temporal gap):\nClaim: 'World War II ended in 1945.'\nFirst-hop evidence: 'World War II involved many countries.'\nComponent breakdown:\n- Event: World War II -> verified as existing\n- End year: missing (only general involvement found)\n- Claimed end year: 1945 -> not verified\nCritical gap: end year of WWII\nQuery: 'World War II end year'",
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
                "reasoning_questions": "What key entities, dates, or relations are present in the passages? What specific information from the claim remains unverified?",
                "example_reasoning": "Example:\nClaim: 'The Eiffel Tower was built in 1887.'\nPassages:\n[1] Eiffel Tower construction | Began in 1887.\nSummary: Construction of the Eiffel Tower began in 1887. This verifies the claim. No gaps remain.",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries",
                "stage_action": "Break down the claim into key components. For each component, list the evidence found so far (from first and second hop summaries) and what is still missing. If all components are verified, output nothing. Otherwise, output a concise search query for the most critical missing piece. Output ONLY the query string or nothing.",
                "reasoning_questions": "What are the key components of the claim (e.g., entities, dates, relations)? For each component, what evidence have we found across both summaries? What evidence is still missing? Which missing piece is most critical for verification? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": "Example 1 (entity gap):\nClaim: 'The Eiffel Tower was built in 1887.'\nFirst-hop summary: 'The Eiffel Tower was completed in 1889.'\nSecond-hop summary: 'SKIPPED'\nComponent breakdown:\n- Entity: Eiffel Tower -> verified\n- Construction start year: missing (only completion year 1889 found)\n- Claimed start year: 1887 -> not verified\nCritical gap: construction start year\nQuery: 'Eiffel Tower construction start year'\n\nExample 2 (temporal gap):\nClaim: 'World War II ended in 1945.'\nFirst-hop summary: 'World War II started in 1939.'\nSecond-hop summary: 'World War II major battles occurred in Europe.'\nComponent breakdown:\n- Event: World War II -> verified\n- Start year: 1939 (verified)\n- End year: missing\n- Claimed end year: 1945 -> not verified\nCritical gap: end year\nQuery: 'World War II end date'",
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
                "reasoning_questions": "What key entities, dates, or relations are present in the passages? What specific information from the claim remains unverified?",
                "example_reasoning": "Example:\nClaim: 'The Eiffel Tower was built in 1887.'\nPassages:\n[1] Construction of the Eiffel Tower | Started on January 28, 1887.\nSummary: Construction of the Eiffel Tower began on January 28, 1887. This verifies the claim. No gaps remain.",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries and generate next search query",
                "stage_action": "Break down the claim into key components. For each component, list the evidence found so far (from first, second, and third hop summaries) and what is still missing. If all components are verified, output nothing. Otherwise, output a concise search query for the most critical missing piece. Output ONLY the query string or nothing.",
                "reasoning_questions": "What are the key components of the claim (e.g., entities, dates, relations)? For each component, what evidence have we found across all summaries? What evidence is still missing? Which missing piece is most critical for verification? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": "Example 1 (entity gap):\nClaim: 'The Eiffel Tower was built in 1887.'\nFirst-hop summary: 'The Eiffel Tower was completed in 1889.'\nSecond-hop summary: 'SKIPPED'\nThird-hop summary: 'Construction began in 1887.'\nComponent breakdown:\n- Entity: Eiffel Tower -> verified\n- Construction start year: 1887 (verified)\n- Claim is fully verified\nNo query needed\n\nExample 2 (temporal gap):\nClaim: 'World War II ended in 1945.'\nFirst-hop summary: 'World War II started in 1939.'\nSecond-hop summary: 'World War II major battles'\nThird-hop summary: 'The war in Europe ended in May 1945.'\nComponent breakdown:\n- Event: World War II -> verified\n- Start year: 1939 (verified)\n- End year in Europe: May 1945 (verified)\n- Claim specifies 1945 which matches\nNo query needed",
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
