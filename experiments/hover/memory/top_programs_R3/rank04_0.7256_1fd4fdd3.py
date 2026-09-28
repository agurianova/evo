def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker verifying claims using Wikipedia evidence. ALWAYS follow these rules:\n- For steps requiring ONLY a query or 'STOP', output EXACTLY that with NO additional text\n- Summarize evidence concisely focusing on claim-relevant facts\n- Stop retrieving when evidence is sufficient",
        "steps": [
            # Step 1: Initial evidence retrieval
            {
                "number": 1,
                "title": "Retrieve initial passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            # Step 2: Summarize initial evidence
            {
                "number": 2,
                "title": "Summarize initial evidence",
                "step_type": "llm",
                "aim": "Extract claim-relevant facts from initial passages",
                "stage_action": (
                    "Analyze the retrieved passages and identify ONLY facts directly supporting or refuting the claim.\n"
                    "Produce a concise bullet-point summary of key evidence."
                ),
                "reasoning_questions": (
                    "Which facts directly prove or disprove the claim?\n"
                    "What specific details are missing for full verification?"
                ),
                "example_reasoning": (
                    "Claim: 'Chernobyl disaster was caused by reactor design flaws'\n"
                    "Passage: 'The Chernobyl accident resulted from a flawed Soviet reactor design and operator errors.'\n"
                    "→ Key fact: Explicitly states reactor design flaw as cause.\n"
                    "Missing: Specific design flaw details (e.g., control rod configuration)."
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query or STOP
            {
                "number": 3,
                "title": "Evaluate evidence sufficiency",
                "step_type": "llm",
                "aim": "Determine if initial evidence is sufficient or generate second-hop query",
                "stage_action": (
                    "If the evidence summary contains ALL facts needed to verify the claim, output 'STOP'.\n"
                    "Otherwise, generate ONE concise search query targeting the MOST critical missing fact.\n"
                    "OUTPUT ONLY THE QUERY OR 'STOP' - NO EXPLANATIONS"
                ),
                "reasoning_questions": (
                    "Is the claim fully verified by current evidence?\n"
                    "What SINGLE missing fact would most advance verification?\n"
                    "How to phrase this as a minimal search query?"
                ),
                "example_reasoning": (
                    "Sufficient evidence case:\n"
                    "Summary: 'Passage confirms reactor design flaw caused Chernobyl disaster'\n"
                    "→ Output: STOP\n\n"
                    "Insufficient evidence case:\n"
                    "Summary: 'Passage states disaster occurred in 1986 but doesn't specify cause'\n"
                    "→ Output: 'Chernobyl disaster primary cause reactor design'"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[2]"},
                },
                "dependencies": [3],
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Extract new facts from second retrieval",
                "stage_action": (
                    "Analyze NEW passages and identify ONLY facts addressing the missing information from step 3.\n"
                    "If no relevant facts found, state 'No additional evidence discovered.'\n"
                    "Output concise bullet points."
                ),
                "reasoning_questions": (
                    "What new facts fill the previous gap?\n"
                    "Do these facts complete verification?\n"
                    "What remains uncertain?"
                ),
                "example_reasoning": (
                    "Previous gap: 'Specific RBMK reactor design flaw'\n"
                    "Passage: 'The RBMK design had a positive void coefficient due to graphite tips on control rods.'\n"
                    "→ New fact: Graphite-tipped control rods caused positive void coefficient.\n\n"
                    "No relevant evidence case:\n"
                    "Passage: 'Chernobyl is a city in Ukraine'\n"
                    "→ Output: No additional evidence discovered."
                ),
                "dependencies": [4],
            },
            # Step 6: Generate third-hop query or STOP
            {
                "number": 6,
                "title": "Final evidence evaluation",
                "step_type": "llm",
                "aim": "Determine if combined evidence is sufficient or generate final query",
                "stage_action": (
                    "Combine initial and new evidence summaries. If ALL claim elements are verified, output 'STOP'.\n"
                    "Otherwise, generate ONE query for the SINGLE most critical remaining gap.\n"
                    "OUTPUT ONLY THE QUERY OR 'STOP' - NO EXPLANATIONS"
                ),
                "reasoning_questions": (
                    "What is the ONE fact still needed for verification?\n"
                    "How to phrase the minimal query for this fact?\n"
                    "Would finding this fact complete verification?"
                ),
                "example_reasoning": (
                    "Sufficient evidence case:\n"
                    "Summary1: 'Design flaw confirmed'\n"
                    "Summary2: 'Graphite control rods identified as flaw'\n"
                    "→ Output: STOP\n\n"
                    "Insufficient evidence case:\n"
                    "Summary1: 'Disaster occurred in 1986'\n"
                    "Summary2: 'Reactor type: RBMK'\n"
                    "→ Output: 'Chernobyl RBMK reactor design flaw specific mechanism'"
                ),
                "dependencies": [2, 5],
            },
            # Step 7: Third-hop retrieval
            {
                "number": 7,
                "title": "Retrieve final passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[5]"},
                },
                "dependencies": [6],
            },
        ],
    }