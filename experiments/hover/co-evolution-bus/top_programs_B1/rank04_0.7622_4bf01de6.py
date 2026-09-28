def entrypoint():
    return {
        "system_prompt": "You are a fact-checking expert. For each step: Summarizers extract ONLY facts directly relevant to the claim. Query generators output ONLY the search query string. Be precise and concise.",
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
                    "List bullet points of key entities (people, places, drugs, conditions) and verifiable facts. "
                    "Do not include opinions or irrelevant details. Include ONLY facts directly relevant to verifying the claim. "
                    "Do not add any information not explicitly present in the retrieved passages."
                ),
                "reasoning_questions": (
                    "1. What are the main entities mentioned?\n"
                    "2. What specific facts (doses, conditions, outcomes) are stated?\n"
                    "3. How do these facts relate to the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Aspirin prevents heart attacks in high-risk patients.'\n"
                    "Passages:\n"
                    "[1] Aspirin | Low-dose aspirin is recommended for secondary prevention of heart attacks.\n"
                    "[2] Heart attack | Primary prevention with aspirin is not generally recommended due to bleeding risks.\n"
                    "- Entities: Aspirin, heart attack\n"
                    "- Facts:\n"
                    "  * Secondary prevention: recommended\n"
                    "  * Primary prevention: not recommended (bleeding risks)\n"
                    "- Relation: Claim specifies high-risk (secondary prevention) — supported."
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
                    "Generate a precise and minimal search query targeting the missing information. "
                    "Include only key entities and necessary context. Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "1. What key fact from the claim is unsupported by first-hop evidence?\n"
                    "2. What specific entity or event should we search for next?"
                ),
                "example_reasoning": "CORRECT: Aspirin willow bark connection\nWRONG: What is the connection between aspirin and willow bark?",
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
                    "and verifiable facts. Exclude redundant information. You may connect related facts that are directly supported "
                    "(e.g., 'salicylic acid derived from willow bark' implies a connection to aspirin). At the end, state the single missing fact "
                    "needed to verify the claim. Do not add any information not directly supported by the passages."
                ),
                "reasoning_questions": (
                    "1. What new entities/facts appear in second-hop passages?\n"
                    "2. How do these connect to first-hop evidence and claim?\n"
                    "3. What single fact is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The drug aspirin is derived from willow bark.'\n"
                    "First-hop summary:\n"
                    "- Entities: Aspirin, willow bark\n"
                    "- Facts:\n"
                    "  * Aspirin: used for pain and fever\n"
                    "  * Willow bark: contains salicin (precursor to salicylic acid)\n"
                    "Second-hop passages:\n"
                    "[1] History of aspirin | Aspirin was developed from salicylic acid, which was derived from willow bark.\n"
                    "Unified summary:\n"
                    "- Entities: Aspirin, willow bark, salicylic acid\n"
                    "- Facts:\n"
                    "  * Aspirin developed from salicylic acid\n"
                    "  * Salicylic acid derived from willow bark\n"
                    "Missing: Confirmation that aspirin is directly synthesized from willow bark (i.e., the full derivation path)"
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
                    "Generate the most precise and minimal query targeting exactly the missing fact. "
                    "Avoid broad terms. Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "1. What single fact would confirm/refute the claim?\n"
                    "2. Which specific source likely contains this fact?"
                ),
                "example_reasoning": "CORRECT: Aspirin synthesis from willow bark\nWRONG: How is aspirin synthesized from willow bark?",
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
