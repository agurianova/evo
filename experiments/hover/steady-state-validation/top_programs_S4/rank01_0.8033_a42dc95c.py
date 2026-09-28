def entrypoint():
    return {
        "system_prompt": "You are an expert evidence retrieval assistant for claim verification. Follow the instructions for each step precisely.\n\n- In steps that generate a search query: output ONLY the search query string, with no additional text, explanations, or formatting.\n- In steps that summarize evidence: output a concise bullet-point list of key facts relevant to the claim, without any extra commentary.\n\nAlways be precise and avoid extraneous text.",
        "steps": [
            # Step 1: First-hop retrieval with deep search
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
                "aim": "Extract key facts from first-hop passages relevant to claim verification",
                "stage_action": "Read retrieved passages and identify the most important facts supporting/refuting the claim. Output a bullet-point list of these facts without commentary.",
                "reasoning_questions": "What are the main entities/events mentioned?\nWhich facts directly relate to the claim?\nAre there critical dates/numbers/details?",
                "example_reasoning": "Example claim: 'The Eiffel Tower was completed in 1887.'\nPassages:\n[1] Eiffel Tower | Construction began in 1887 and was completed in 1889.\nRelevant facts:\n- Construction began in 1887\n- Completion occurred in 1889",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing evidence and generate precise second-hop search query",
                "stage_action": "Based on first-hop summary, determine needed evidence and write a concise search query. Output ONLY the query string.",
                "reasoning_questions": "What specific information is still missing?\nWhich entities/concepts need investigation?",
                "example_reasoning": "Example claim: 'The Eiffel Tower was completed in 1887.'\nFirst-hop summary:\n- Construction began in 1887\n- Completion occurred in 1889\nMissing: Official completion year confirmation\nQuery: Eiffel Tower official completion year",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval with deep search
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
                "aim": "Extract key facts from second-hop passages relevant to claim verification",
                "stage_action": "Read retrieved passages and identify the most important facts supporting/refuting the claim. Output a bullet-point list of these facts without commentary.",
                "reasoning_questions": "What new information does this provide?\nHow does it connect to first-hop evidence?\nWhat gaps remain?",
                "example_reasoning": "Example claim: 'The Eiffel Tower was completed in 1887.'\nPassages:\n[1] Paris Exposition | The Eiffel Tower opened in 1889 as the exposition centerpiece.\nRelevant facts:\n- Tower opened to public in 1889\n- Served as exposition centerpiece",
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify remaining gaps and generate precise third-hop search query",
                "stage_action": "Based on combined first/second-hop evidence, determine needed evidence and write a concise search query. Output ONLY the query string.",
                "reasoning_questions": "What gaps remain after both hops?\nWhat specific information would conclusively verify the claim?",
                "example_reasoning": "Example claim: 'The Eiffel Tower was completed in 1887.'\nFirst-hop summary:\n- Construction began 1887, completed 1889\nSecond-hop summary:\n- Opened to public in 1889\nMissing: Official government completion records\nQuery: Eiffel Tower French government completion records",
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval with deep search
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
                "aim": "Extract key facts from third-hop passages relevant to claim verification",
                "stage_action": "Read retrieved passages and identify the most important facts supporting/refuting the claim. Output a bullet-point list of these facts without commentary.",
                "reasoning_questions": "What conclusive evidence does this provide?\nHow does it resolve previous gaps?\nIs the claim fully verifiable now?",
                "example_reasoning": "Example claim: 'The Eiffel Tower was completed in 1887.'\nPassages:\n[1] French Archives | Official completion certificate dated March 31, 1889.\nRelevant facts:\n- Official completion date: March 31, 1889",
                "dependencies": [7],
            },
            # Step 9: Generate fourth-hop query with gap analysis
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Identify any remaining evidence gaps and generate fourth-hop search query",
                "stage_action": "Based on all evidence summaries, determine if gaps remain. If yes, write concise search query. If no gaps, output 'NO_QUERY_NEEDED'. Output ONLY the query or 'NO_QUERY_NEEDED'.",
                "reasoning_questions": "Is the claim fully supported/refuted by current evidence?\nWhat specific missing information would change the outcome?",
                "example_reasoning": "Example claim: 'The Eiffel Tower was completed in 1887.'\nFirst-hop summary:\n- Construction began 1887, completed 1889\nSecond-hop summary:\n- Opened to public in 1889\nThird-hop summary:\n- Official completion date: March 31, 1889\nAnalysis: Claim states 1887 but evidence shows 1889 completion\nQuery: NO_QUERY_NEEDED",
                "dependencies": [2, 5, 8],
            },
            # Step 10: Fourth-hop retrieval with deep search
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
