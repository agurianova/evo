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
                    "Do not include opinions or irrelevant details. Include ONLY facts directly relevant to verifying the claim and present in the retrieved passages."
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
                    "Based on the bullet-point summary, determine what specific information is missing. "
                    "Write a search query including key entities and dates. Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "1. What key fact from the claim is unsupported by first-hop evidence?\n"
                    "2. What specific entity or event should we search for next?\n"
                    "3. How can you phrase the query as a minimal string of words (e.g., 'Aspirin secondary prevention guidelines') without any extra text, questions, or punctuation? Example of wrong output: 'What are the secondary prevention guidelines for aspirin?'"
                ),
                "example_reasoning": "Aspirin secondary prevention guidelines",
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
                    "and verifiable facts. Exclude redundant information. Do not add any information not present in the retrieved passages. At the end, state the single missing fact needed to verify the claim."
                ),
                "reasoning_questions": (
                    "1. What new entities/facts appear in second-hop passages?\n"
                    "2. How do these connect to first-hop evidence and claim?\n"
                    "3. What single fact is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Marie Curie's daughter won a Nobel Prize for the discovery of artificial radioactivity.'\n"
                    "First-hop summary:\n"
                    "- Entities: Marie Curie, daughter\n"
                    "- Facts:\n"
                    "  * Daughter won a Nobel Prize in Chemistry\n"
                    "Second-hop passages:\n"
                    "[1] Irene Joliot-Curie | Irene Joliot-Curie was a French scientist who won the Nobel Prize in Chemistry in 1935.\n"
                    "Unified summary:\n"
                    "- Entities: Marie Curie, Irene Joliot-Curie\n"
                    "- Facts:\n"
                    "  * Irene Joliot-Curie is Marie Curie's daughter\n"
                    "  * Irene won the Nobel Prize in Chemistry in 1935\n"
                    "Missing: The discovery of artificial radioactivity as the reason for the Nobel Prize"
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
                    "Generate the most precise and minimal attribute-based query targeting exactly the missing fact (e.g., 'birthplace of Marie Curie'). "
                    "The query must be a string of words separated by spaces with no punctuation or extra text. Output ONLY the query string."
                ),
                "reasoning_questions": (
                    "1. What single fact would confirm/refute the claim?\n"
                    "2. Which specific source likely contains this fact?\n"
                    "3. How can you phrase the query as a minimal attribute-based phrase (e.g., 'artificial radioactivity discovery Irene Joliot-Curie') without any extra words or punctuation? Example of wrong output: 'What is the reason for Irene Joliot-Curie's Nobel Prize?'"
                ),
                "example_reasoning": "artificial radioactivity discovery Irene Joliot-Curie",
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
