def entrypoint():
    return {
        "system_prompt": (
            "You are an expert fact-checker assistant. Your task is to verify claims by retrieving relevant evidence from Wikipedia. "
            "Follow these principles:\n"
            "- Always base your reasoning on the retrieved passages and the original claim.\n"
            "- For query generation steps, output ONLY the search query without any additional text.\n"
            "- For summarization steps, output ONLY key facts directly relevant to the claim without any reasoning or additional text.\n"
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
            # Step 2: Summarize first-hop evidence with gap focus and clean output
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the first-hop retrieved passages relevant to the claim and identify unverified aspects.",
                "stage_action": (
                    "Read the retrieved passages and output ONLY key facts directly relevant to the claim, without any reasoning. "
                    "Then, state the specific claim aspect that remains unverified."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified based on the current evidence?",
                "example_reasoning": "Claim: 'Einstein was born in Germany'. Evidence: ['[1] Ulm | Einstein was born in Ulm, Germany.'] → Gap: 'Germany is a country, but Ulm is a city; confirm Ulm is in Germany.'",
                "dependencies": [1],
            },
            # Step 3: Generate first second-hop query
            {
                "number": 3,
                "title": "Generate first second-hop query",
                "step_type": "llm",
                "aim": "Identify the first logical piece of evidence to verify the claim based on the first-hop summary.",
                "stage_action": (
                    "Based on the summary of the first-hop evidence and the original claim, determine what specific information is still needed for the first gap. "
                    "Formulate a concise search query. Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: For claim 'Einstein was born in Germany', if evidence mentions Ulm, output: 'Ulm Germany'",
                "dependencies": [2],
            },
            # Step 4: Generate second second-hop query (independent branch)
            {
                "number": 4,
                "title": "Generate second second-hop query",
                "step_type": "llm",
                "aim": "Identify a second, independent piece of evidence to verify the claim based on the first-hop summary.",
                "stage_action": (
                    "Based on the summary of the first-hop evidence and the original claim, determine a different specific information gap. "
                    "Formulate a concise search query. Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: For claim 'Einstein was born in Germany', if evidence mentions Ulm, output: 'Einstein birthplace city'",
                "dependencies": [2],
            },
            # Step 5: Retrieve for first second-hop query (deep)
            {
                "number": 5,
                "title": "Retrieve first second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[2]"},  # output of step3
                },
                "dependencies": [3],
            },
            # Step 6: Retrieve for second second-hop query (deep)
            {
                "number": 6,
                "title": "Retrieve second second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[3]"},  # output of step4
                },
                "dependencies": [4],
            },
            # Step 7: Merge and summarize both second-hop results
            {
                "number": 7,
                "title": "Merge and summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Merge and extract key facts from both second-hop retrieved passages relevant to the claim and identify remaining gaps.",
                "stage_action": (
                    "Read both sets of retrieved passages and output ONLY key facts directly relevant to the claim, without any reasoning. "
                    "Then, state the specific claim aspect that remains unverified after considering all evidence so far."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified based on the current evidence from all hops?",
                "example_reasoning": "Claim: 'Marie Curie won two Nobel Prizes'. Evidence from first hop: ['[1] Nobel Prize in Physics | ...']. Evidence from second hop (query1): ['[1] Nobel Prize in Chemistry | ...']. → Gap: 'No evidence that both prizes were won by Marie Curie'",
                "dependencies": [5, 6],
            },
            # Step 8: Generate third-hop query
            {
                "number": 8,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify the precise missing piece of evidence needed to complete verification, using all available evidence.",
                "stage_action": (
                    "Integrate the evidence from the first and second hops (both branches). Identify the exact gap that remains. "
                    "Formulate a highly specific search query to find the missing piece. Output ONLY the search query, no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "Example: For claim 'Marie Curie won two Nobel Prizes', if evidence shows Physics and Chemistry prizes but not that she won both, output: 'Marie Curie two Nobel Prizes'",
                "dependencies": [2, 7],
            },
            # Step 9: Retrieve third-hop passages (deep)
            {
                "number": 9,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[7]"},  # output of step8
                },
                "dependencies": [8],
            },
            # Step 10: Summarize third-hop evidence
            {
                "number": 10,
                "title": "Summarize third-hop evidence",
                "step_type": "llm",
                "aim": "Extract key facts from the third-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read the retrieved passages and output ONLY key facts directly relevant to the claim, without any reasoning. "
                    "Then, state the specific claim aspect that remains unverified."
                ),
                "reasoning_questions": "What specific claim aspect remains unverified based on the current evidence?",
                "example_reasoning": "Claim: 'The Eiffel Tower was built in 1889'. Evidence: ['[1] Construction | The Eiffel Tower was completed in 1889.'] → Gap: 'None'",
                "dependencies": [9],
            },
        ],
    }