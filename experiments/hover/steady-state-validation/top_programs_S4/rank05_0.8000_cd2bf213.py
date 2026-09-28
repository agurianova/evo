def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Always follow instructions precisely. For query generation steps, output ONLY the search query string with no additional text, formatting, or explanations.",
        "steps": [
            # Step 1: First-hop retrieval with deeper search (k=10 for critical first hop)
            {
                "number": 1,
                "title": "Retrieve initial passages",
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
                "aim": "Extract key facts from the retrieved passages relevant to the claim.",
                "stage_action": (
                    "Read all retrieved passages and identify facts that are directly relevant "
                    "to verifying the claim. Summarize the most important evidence found."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Space exploration | The first human spaceflight was in 1961.\n"
                    "Relevant passage: [1] states the moon landing date.\n"
                    "Key fact: Apollo 11 landed on the moon on July 20, 1969.\n"
                    "Summary: 'Apollo 11 landed on the moon on July 20, 1969.'"
                ),
                "dependencies": [1],
            },
            # Step 3: Generate second-hop query as OR combination
            {
                "number": 3,
                "title": "Generate second-hop OR query",
                "step_type": "llm",
                "aim": "Identify two complementary missing evidence pieces and generate a single OR query.",
                "stage_action": (
                    "Based on the evidence summary, determine two specific, complementary pieces of evidence still needed to "
                    "fully verify the claim. Write a single search query in the format 'query1 OR query2' to find both pieces. "
                    "Output ONLY the query string with no additional text."
                ),
                "reasoning_questions": (
                    "1. What are two specific, complementary pieces of information missing from the current evidence?\n"
                    "2. How can you phrase two concise queries that capture these missing pieces?\n"
                    "3. Combine them with 'OR' to form a single query."
                ),
                "example_reasoning": (
                    "Summary: 'Apollo 11 landed on the moon, but the year and astronauts are not specified.'\n"
                    "Missing 1: year of moon landing\n"
                    "Missing 2: names of astronauts\n"
                    "moon landing year OR Apollo 11 astronauts"
                ),
                "dependencies": [2],
            },
            # Step 4: Second-hop retrieval with standard depth (k=7 for intermediate hop)
            {
                "number": 4,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            # Step 5: Combine first and second hop evidence with missing enumeration
            {
                "number": 5,
                "title": "Combine evidence and list gaps",
                "step_type": "llm",
                "aim": "Create unified summary of first two hops and explicitly list remaining gaps.",
                "stage_action": (
                    "Integrate the first-hop evidence summary (step2) with the second-hop retrieved passages (step4). "
                    "Produce a comprehensive summary of all relevant facts. Then, list specific missing evidence under 'Missing:'. "
                    "Do not include any other sections."
                ),
                "reasoning_questions": (
                    "1. What is the original claim?\n"
                    "2. What evidence was found in first hop?\n"
                    "3. What evidence was found in second hop?\n"
                    "4. How do these connect to verify the claim?\n"
                    "5. What specific evidence is still missing?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "First hop summary: 'Apollo 11 landed on the moon on July 20, 1969.'\n"
                    "Second hop passages:\n"
                    "[1] Apollo 11 crew | Neil Armstrong and Buzz Aldrin were astronauts.\n"
                    "[2] Moon landing | The event was broadcast live worldwide.\n"
                    "Combined evidence: 'Apollo 11, with astronauts Neil Armstrong and Buzz Aldrin, landed on the moon on July 20, 1969.'\n"
                    "Missing: Neil Armstrong being the first person to step on the moon."
                ),
                "dependencies": [2, 4],
            },
            # Step 6: Generate third-hop query
            {
                "number": 6,
                "title": "Generate third-hop query",
                "step_type": "llm",
                "aim": "Generate precise query for missing evidence from combined summary.",
                "stage_action": (
                    "Based on the 'Missing:' section in the combined evidence summary (step5), generate a search query "
                    "to find the missing evidence. Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "1. What specific evidence is listed in the 'Missing:' section?\n"
                    "2. What search terms would most precisely retrieve this evidence?"
                ),
                "example_reasoning": (
                    "Combined evidence (step5):\n"
                    "Combined evidence: 'Apollo 11 landed on the moon on July 20, 1969.'\n"
                    "Missing: Neil Armstrong being the first person to step on the moon.\n"
                    "Neil Armstrong first man moon"
                ),
                "dependencies": [5],
            },
            # Step 7: Third-hop retrieval with standard depth (k=7 for intermediate hop)
            {
                "number": 7,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            # Step 8: Combine all evidence so far with missing enumeration
            {
                "number": 8,
                "title": "Combine evidence and list final gaps",
                "step_type": "llm",
                "aim": "Create unified summary of first three hops and explicitly list remaining gaps.",
                "stage_action": (
                    "Integrate the combined evidence from step5 with the third-hop retrieved passages (step7). "
                    "Produce a comprehensive summary of all relevant facts. Then, list specific missing evidence under 'Missing:'. "
                    "Do not include any other sections."
                ),
                "reasoning_questions": (
                    "1. What evidence was found in the first two hops (step5)?\n"
                    "2. What new evidence was found in third hop?\n"
                    "3. How do these connect to verify the claim?\n"
                    "4. What specific evidence is still missing?"
                ),
                "example_reasoning": (
                    "Step5 combined evidence: 'Apollo 11 landed on the moon on July 20, 1969.'\n"
                    "Step5 missing: Neil Armstrong being the first person to step on the moon.\n"
                    "Third hop passages:\n"
                    "[1] Neil Armstrong | He was the first person to step on the moon.\n"
                    "Combined evidence: 'Apollo 11 landed on the moon on July 20, 1969, with Neil Armstrong as the first person to step on the moon.'\n"
                    "Missing: None."
                ),
                "dependencies": [5, 7],
            },
            # Step 9: Generate fourth-hop query
            {
                "number": 9,
                "title": "Generate fourth-hop query",
                "step_type": "llm",
                "aim": "Generate precise query for final missing evidence if any.",
                "stage_action": (
                    "Based on the 'Missing:' section in the combined evidence summary (step8), generate a search query "
                    "to find the missing evidence. Output ONLY the search query string."
                ),
                "reasoning_questions": (
                    "1. What specific evidence is listed in the 'Missing:' section?\n"
                    "2. What search terms would most precisely retrieve this evidence?"
                ),
                "example_reasoning": (
                    "Combined evidence (step8):\n"
                    "Combined evidence: 'Apollo 11 landed on the moon on July 20, 1969.'\n"
                    "Missing: Official NASA confirmation document.\n"
                    "NASA moon landing official confirmation"
                ),
                "dependencies": [8],
            },
            # Step 10: Fourth-hop retrieval with deeper search (k=10 for critical last hop)
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
