def entrypoint():
    return {
        "system_prompt": "You are an expert fact-checker for multi-hop claims. \n- As a summarizer: Extract ONLY claim-relevant facts; omit noise.\n- As a query generator: Output ONLY the search query string (no extra text).",
        "steps": [
            # Step 1: First-hop retrieval (frozen tool step)
            {
                "number": 1,
                "title": "Retrieve first-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
                "frozen": True,
            },
            # Step 2: Summarize first-hop evidence
            {
                "number": 2,
                "title": "Summarize first-hop evidence",
                "step_type": "llm",
                "aim": "Extract key entities and factual claims from retrieved passages relevant to the claim.",
                "stage_action": (
                    "List bullet points of key entities (people, places, dates) and verifiable facts that are DIRECTLY RELEVANT to the claim. "
                    "Exclude opinions, irrelevant details, and potential noise. Focus ONLY on facts that help verify the claim."
                ),
                "reasoning_questions": (
                    "1. What are the main entities mentioned?\n"
                    "2. What specific facts (dates, numbers, events) are stated?\n"
                    "3. How do these facts relate to the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Aspirin prevents heart attacks in high-risk patients.'\n"
                    "Passages:\n"
                    "[1] Aspirin | It is used for secondary prevention of heart attacks in patients with prior cardiovascular events.\n"
                    "- Entities: Aspirin, heart attacks, secondary prevention\n"
                    "- Facts: Aspirin reduces risk of subsequent heart attacks in patients with prior cardiovascular events."
                ),
                "dependencies": [1],
                "frozen": False,
            },
            # Step 3: Generate second-hop query
            {
                "number": 3,
                "title": "Generate second-hop query",
                "step_type": "llm",
                "aim": "Identify missing link to verify claim and generate focused search query.",
                "stage_action": (
                    "Based on the bullet-point summary, determine the single most critical missing fact. "
                    "Write a highly specific search query using entities/dates from evidence. Include specific entities and dates. "
                    "Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "1. What key fact from the claim is unsupported by first-hop evidence?\n"
                    "2. What specific entity or event should we search for next?"
                ),
                "example_reasoning": (
                    "Reasoning (internal):\n"
                    "- Claim: 'Aspirin prevents heart attacks in high-risk patients.'\n"
                    "- Summary shows aspirin is for secondary prevention (after heart event), not primary prevention (for at-risk without event).\n"
                    "Output ONLY the query string:\n"
                    "Aspirin primary prevention heart attack"
                ),
                "dependencies": [2],
                "frozen": False,
            },
            # Step 4: Second-hop retrieval (frozen tool step)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
                "frozen": True,
            },
            # Step 5: Summarize second-hop evidence
            {
                "number": 5,
                "title": "Summarize second-hop evidence",
                "step_type": "llm",
                "aim": "Combine first-hop and second-hop evidence into unified bullet-point summary.",
                "stage_action": (
                    "Integrate first-hop summary with second-hop passages. List bullet points of all key entities "
                    "and verifiable facts. Exclude redundant information. Ensure all verification-critical facts are present. "
                    "At the end, state: 'Missing: [one-sentence description of the single most critical missing fact]'"
                ),
                "reasoning_questions": (
                    "1. What new entities/facts appear in second-hop passages?\n"
                    "2. How do these connect to first-hop evidence and claim?\n"
                    "3. What is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Aspirin prevents heart attacks in high-risk patients.'\n"
                    "First-hop summary:\n"
                    "- Entities: Aspirin, heart attacks, secondary prevention\n"
                    "- Facts: Aspirin reduces risk of subsequent heart attacks in patients with prior cardiovascular events.\n"
                    "Second-hop passages:\n"
                    "[1] Primary prevention | Aspirin's role in primary prevention is less clear and may depend on individual risk factors.\n"
                    "Unified summary:\n"
                    "- Entities: Aspirin, heart attacks, secondary prevention, primary prevention\n"
                    "- Facts: Aspirin is effective for secondary prevention; evidence for primary prevention is mixed.\n"
                    "Missing: Results of the ASPREE trial for primary prevention in elderly patients."
                ),
                "dependencies": [2, 4],
                "frozen": False,
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Identify single most critical missing fact and generate precise search query.",
                "stage_action": (
                    "Based on unified evidence, determine the one essential fact still missing. "
                    "Write a highly specific search query using entities/dates from evidence. Include specific trial names if mentioned. "
                    "Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "1. What single fact would confirm/refute the claim?\n"
                    "2. Which specific source likely contains this fact?"
                ),
                "example_reasoning": (
                    "Reasoning (internal):\n"
                    "- Claim: 'Aspirin prevents heart attacks in high-risk patients.'\n"
                    "- Unified summary states evidence for primary prevention is mixed, specifically missing ASPREE trial results.\n"
                    "Output ONLY the query string:\n"
                    "ASPREE trial aspirin primary prevention elderly"
                ),
                "dependencies": [5],
                "frozen": False,
            },
            # Step 7: Third-hop retrieval (frozen tool step, deeper search)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
                "frozen": True,
            },
        ],
    }
