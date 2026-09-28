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
                "reasoning_questions": "What key facts from the passages directly support or contradict the claim? What specific information is missing to fully verify the claim?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages: [1] Eiffel Tower | Completed in 1889. Height: 330 meters.\n"
                    "Summary: The Eiffel Tower was completed in 1889.\n"
                    "Gap: The claim states 'built in 1887', but the evidence only provides the completion year. Missing: construction start year.\n\n"
                    "Example 2:\n"
                    "Claim: 'World War II ended in 1945.'\n"
                    "Retrieved passages: [1] World War II | Began in 1939. [2] D-Day | June 6, 1944.\n"
                    "Summary: World War II began in 1939 and D-Day occurred in 1944.\n"
                    "Gap: The evidence does not state when World War II ended. Missing: end year of World War II."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed and generate next search query",
                "stage_action": (
                    "Consider the claim and the first-hop evidence summary. \n"
                    "1. List the evidence you have found so far that supports or contradicts the claim.\n"
                    "2. Identify the specific missing information required to verify the claim.\n"
                    "3. If the claim can be verified with the current evidence, output nothing.\n"
                    "4. Otherwise, output a concise search query for the missing evidence. \n"
                    "Output ONLY the query string or nothing."
                ),
                "reasoning_questions": "What key entities or relations are missing to verify the claim? What specific information would bridge the gap between the claim and current evidence? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop evidence summary: The Eiffel Tower was completed in 1889.\n"
                    "Evidence found: Completion year (1889).\n"
                    "Missing: Construction start year.\n"
                    "Query: 'Eiffel Tower construction start year'\n\n"
                    "Example 2:\n"
                    "Claim: 'World War II ended in 1945.'\n"
                    "First-hop evidence summary: World War II began in 1939 and D-Day occurred in 1944.\n"
                    "Evidence found: Start year (1939), D-Day (1944).\n"
                    "Missing: End year of World War II.\n"
                    "Query: 'World War II end year'"
                ),
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
                "reasoning_questions": "What key facts from these passages directly support or contradict the claim? What specific information is still missing to fully verify the claim?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages (second hop): [1] Construction of Eiffel Tower | Began in January 1887 and completed in March 1889.\n"
                    "Summary: Construction of the Eiffel Tower began in January 1887.\n"
                    "Gap: The evidence confirms the construction start year (1887) as stated in the claim. No gaps remain for verification.\n\n"
                    "Example 2:\n"
                    "Claim: 'World War II ended in 1945.'\n"
                    "Retrieved passages (second hop): [1] World War II timeline | Major events of 1944 included D-Day.\n"
                    "Summary: World War II had major events in 1944, including D-Day.\n"
                    "Gap: The evidence does not state when World War II ended. Missing: end year of World War II."
                ),
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries",
                "stage_action": (
                    "Consider the claim, the first-hop evidence summary, and the second-hop evidence summary. \n"
                    "1. List the evidence you have found so far that supports or contradicts the claim.\n"
                    "2. Identify the specific missing information required to verify the claim.\n"
                    "3. If the claim can be verified with the current evidence, output nothing.\n"
                    "4. Otherwise, output a concise search query for the missing evidence. \n"
                    "Output ONLY the query string or nothing."
                ),
                "reasoning_questions": "What critical gaps remain after reviewing all evidence? What specific query would target the missing verification element? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop evidence summary: The Eiffel Tower was completed in 1889.\n"
                    "Second-hop evidence summary: Construction of the Eiffel Tower began in January 1887.\n"
                    "Evidence found: Completion year (1889), Construction start year (1887).\n"
                    "Missing: None. The claim is verified.\n"
                    "Query: \n\n"
                    "Example 2:\n"
                    "Claim: 'World War II ended in 1945.'\n"
                    "First-hop evidence summary: World War II began in 1939.\n"
                    "Second-hop evidence summary: World War II had major events in 1944, including D-Day.\n"
                    "Evidence found: Start year (1939), Events in 1944.\n"
                    "Missing: End year of World War II.\n"
                    "Query: 'World War II end year'"
                ),
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
                "reasoning_questions": "What key facts from these passages directly support or contradict the claim? What specific information is still missing to fully verify the claim?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "Retrieved passages (third hop): [1] Eiffel Tower history | Construction started in 1887 and took 2 years.\n"
                    "Summary: Construction of the Eiffel Tower started in 1887 and took 2 years.\n"
                    "Gap: The evidence confirms the construction start year (1887) and duration. No gaps remain for verification.\n\n"
                    "Example 2:\n"
                    "Claim: 'World War II ended in 1945.'\n"
                    "Retrieved passages (third hop): [1] End of World War II | Officially ended on September 2, 1945.\n"
                    "Summary: World War II officially ended on September 2, 1945.\n"
                    "Gap: The evidence confirms the end year (1945) as stated in the claim. No gaps remain for verification."
                ),
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Determine if more evidence is needed considering all available summaries and generate next search query",
                "stage_action": (
                    "Consider the claim, the first-hop, second-hop, and third-hop evidence summaries (skip any marked 'SKIPPED'). \n"
                    "1. List the evidence you have found so far that supports or contradicts the claim.\n"
                    "2. Identify the specific missing information required to verify the claim.\n"
                    "3. If the claim can be verified with the current evidence, output nothing.\n"
                    "4. Otherwise, output a concise search query for the missing evidence. \n"
                    "Output ONLY the query string or nothing."
                ),
                "reasoning_questions": "What critical gaps remain after reviewing all evidence? What specific query would target the missing verification element? What type of gap is it (entity, temporal, causal)?",
                "example_reasoning": (
                    "Example 1:\n"
                    "Claim: 'The Eiffel Tower was built in 1887.'\n"
                    "First-hop evidence summary: The Eiffel Tower was completed in 1889.\n"
                    "Second-hop evidence summary: Construction of the Eiffel Tower began in January 1887.\n"
                    "Third-hop evidence summary: Construction took 2 years.\n"
                    "Evidence found: Completion year (1889), Construction start year (1887), Duration (2 years).\n"
                    "Missing: None. The claim is verified.\n"
                    "Query: \n\n"
                    "Example 2:\n"
                    "Claim: 'World War II ended in 1945.'\n"
                    "First-hop evidence summary: World War II began in 1939.\n"
                    "Second-hop evidence summary: World War II had major events in 1944, including D-Day.\n"
                    "Third-hop evidence summary: World War II officially ended on September 2, 1945.\n"
                    "Evidence found: Start year (1939), Events in 1944, End date (Sept 2, 1945).\n"
                    "Missing: None. The claim is verified.\n"
                    "Query: "
                ),
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
