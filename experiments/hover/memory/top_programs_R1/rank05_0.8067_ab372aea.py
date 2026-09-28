def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker. Your task is to verify claims by retrieving relevant evidence from Wikipedia. Always focus on the original claim and identify precise gaps in the evidence to formulate targeted search queries. Common gap types include: causation (mechanism, directionality), temporal sequence, quantitative magnitude, ruling out alternatives, and experimental evidence.",
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
            # Step 2: Generate first second-hop query
            {
                "number": 2,
                "title": "Generate second-hop query 1",
                "step_type": "llm",
                "aim": "Identify one missing information aspect from first-hop evidence and generate a targeted search query.",
                "stage_action": (
                    "Review the first-hop retrieved passages and the original claim. Identify one specific information gap that prevents full verification. "
                    "Formulate a concise search query to address this gap. Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "What key fact from the claim is not addressed by the first-hop evidence? "
                    "What entities or relationships need verification?"
                ),
                "example_reasoning": (
                    "The claim states 'Entity A causes Outcome B'. The first-hop passages mention Entity A and Outcome B but do not establish causation. "
                    "I need evidence of a direct causal mechanism. "
                    "Query: 'evidence that Entity A causes Outcome B through Mechanism X'"
                ),
                "dependencies": [1],
            },
            # Step 3: First second-hop retrieval
            {
                "number": 3,
                "title": "Retrieve second-hop passages (query 1)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[1]"},  # Step2 output
                },
                "dependencies": [2],
            },
            # Step 4: Generate second second-hop query (adaptive)
            {
                "number": 4,
                "title": "Generate second-hop query 2 (adaptive)",
                "step_type": "llm",
                "aim": "Identify a different missing information aspect using all available evidence and generate an alternative targeted query.",
                "stage_action": (
                    "Review the first-hop (step1) and first second-hop (step3) retrieved passages along with the original claim. "
                    "Identify a distinct information gap that prevents verification. "
                    "Formulate a concise alternative search query. Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "1. List all gaps in the evidence (with bullet points). "
                    "2. What key evidence is still missing? "
                    "3. Formulate a query to address the most critical gap."
                ),
                "example_reasoning": (
                    "Gaps:\n"
                    "- First-hop and first second-hop show Entity A and Outcome B but no mechanism.\n"
                    "- They also do not rule out alternative causes.\n"
                    "The most critical gap is the lack of mechanism.\n"
                    "Query: 'mechanism by which Entity A causes Outcome B'"
                ),
                "dependencies": [1, 3],
            },
            # Step 5: Second second-hop retrieval
            {
                "number": 5,
                "title": "Retrieve second-hop passages (query 2)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[3]"},  # Step4 output
                },
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query (robust)
            {
                "number": 6,
                "title": "Generate third-hop query (robust)",
                "step_type": "llm",
                "aim": "Identify remaining gaps after reviewing all evidence and generate a final targeted query.",
                "stage_action": (
                    "Review the first-hop (step1), second-hop query1 results (step3), and second-hop query2 results (step5) along with the original claim. "
                    "Identify the most critical missing information for verification. "
                    "Formulate a concise search query to find that information. Output exactly one line of text, no other content."
                ),
                "reasoning_questions": (
                    "1. List all gaps in the evidence (with bullet points). "
                    "2. What key evidence is still missing? "
                    "3. Which gap is most critical for confirming/refuting the claim?"
                ),
                "example_reasoning": (
                    "Gaps:\n"
                    "- No evidence of direct causal mechanism between Entity A and Outcome B.\n"
                    "- No ruling out of alternative causes.\n"
                    "- No experimental evidence.\n"
                    "The most critical gap is the lack of experimental evidence.\n"
                    "Query: 'controlled experiments showing Entity A causes Outcome B'"
                ),
                "dependencies": [1, 3, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},  # Step6 output
                },
                "dependencies": [6],
            },
        ],
    }