def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving and synthesizing evidence from Wikipedia. Always follow these principles:\n- Be thorough: aim to find all relevant evidence to verify the claim.\n- Be contextually appropriate: use broad queries when exploring new angles, specific queries when targeting known gaps.\n- When summarizing, include ALL facts directly relevant to the claim and integrate evidence comprehensively across all available passages.",
        "steps": [
            # Step 1: Initial broad retrieval (k=10)
            {
                "number": 1,
                "title": "Initial broad retrieval",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize first-hop evidence comprehensively
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract ALL key facts from the first-hop retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify ALL facts that are relevant to verifying the claim. "
                    "Produce a comprehensive summary that includes every relevant fact. Do not generate a search query."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query (contextually appropriate)
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Generate a contextually appropriate search query for the next hop to find missing evidence.",
                "stage_action": (
                    "Based on the evidence summary, identify the most critical missing piece of evidence and "
                    "generate a contextually appropriate search query (broad when exploring new angles, specific when targeting known gaps) to find it. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval (k=10)
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
            # Step 5: Integrate first and second hop evidence comprehensively
            {
                "number": 5,
                "title": "Integrate first and second hop evidence",
                "step_type": "llm",
                "aim": "Combine ALL evidence from first and second hops into comprehensive evidence.",
                "stage_action": (
                    "Read the raw passages from the first-hop (Step 1) and second-hop (Step 4) and extract ALL key facts relevant to the claim. "
                    "Produce a unified comprehensive summary covering every relevant fact from both hops. Do not generate a search query."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4],
            },
            # Step 6: Generate third-hop query (contextually appropriate)
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate a contextually appropriate search query for the next hop to find missing evidence.",
                "stage_action": (
                    "Based on the comprehensive evidence summary, identify the most critical missing piece of evidence and "
                    "generate a contextually appropriate search query (broad when exploring new angles, specific when targeting known gaps) to find it. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval (k=10)
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
            # Step 8: Integrate all evidence comprehensively
            {
                "number": 8,
                "title": "Integrate all evidence",
                "step_type": "llm",
                "aim": "Combine ALL evidence from all hops into comprehensive evidence.",
                "stage_action": (
                    "Read the raw passages from the first-hop (Step 1), second-hop (Step 4), and third-hop (Step 7) and extract ALL key facts relevant to the claim. "
                    "Produce a unified comprehensive summary covering every relevant fact from all hops. Do not generate a search query."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [1, 4, 7],
            },
            # Step 9: Generate fourth-hop query (contextually appropriate)
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate a contextually appropriate search query for the next hop to find missing evidence.",
                "stage_action": (
                    "Based on the comprehensive evidence summary, identify the most critical missing piece of evidence and "
                    "generate a contextually appropriate search query (broad when exploring new angles, specific when targeting known gaps) to find it. "
                    "Output ONLY the query string, with no additional text."
                ),
                "reasoning_questions": "<none>",
                "example_reasoning": "<none>",
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval (k=10)
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