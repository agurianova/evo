def entrypoint():
    return {
        "system_prompt": "You are an expert in multi-hop claim verification. Always follow instructions precisely. For query generation steps, output ONLY the search query string with no additional text, formatting, or explanations.",
        "steps": [
            {
                "number": 1,
                "title": "Retrieve initial passages (first hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$outer_context"},
                },
                "dependencies": [],
            },
            {
                "number": 2,
                "title": "Analyze first-hop evidence and generate second-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. Then, identify the specific information still missing to verify the claim. "
                    "Finally, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine terms). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?\n"
                    "5. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "6. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Summary: Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.\n"
                    "Missing: Neil Armstrong's role as the first person to step on the moon.\n"
                    "Neil Armstrong first man moon OR Neil Armstrong first step moon OR first person moon landing"
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Retrieve second-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Analyze second-hop evidence and generate third-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. Then, identify the specific information still missing to verify the claim. "
                    "Finally, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine terms). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?\n"
                    "5. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "6. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous context: Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.\n"
                    "Passages:\n"
                    "[1] Moon landing | Neil Armstrong was the first human to step onto the lunar surface.\n"
                    "Summary: Neil Armstrong was the first human to step onto the lunar surface during Apollo 11.\n"
                    "Missing: Verification of the exact time Armstrong stepped on the moon.\n"
                    "Neil Armstrong step time moon OR moon landing timestamp OR first step moon time"
                ),
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Retrieve third-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Analyze third-hop evidence and generate fourth-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. Then, identify the specific information still missing to verify the claim. "
                    "Finally, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine terms). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?\n"
                    "5. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "6. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous context: Apollo 11 landed on the moon on July 20, 1969.\n"
                    "Passages:\n"
                    "[1] Historical events | The Apollo 11 mission concluded in 1969.\n"
                    "Summary: The Apollo 11 mission concluded in 1969.\n"
                    "Missing: Official NASA confirmation of the moon landing year.\n"
                    "NASA moon landing year confirmation OR Apollo 11 mission year OR official NASA moon landing records"
                ),
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Retrieve fourth-hop passages",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Analyze fourth-hop evidence and generate fifth-hop query",
                "step_type": "llm",
                "aim": "Extract key facts from retrieved passages, identify missing evidence, and generate a precise search query for the next hop.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. Then, identify the specific information still missing to verify the claim. "
                    "Finally, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine terms). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?\n"
                    "5. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "6. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous context: The Apollo 11 mission concluded in 1969.\n"
                    "Passages:\n"
                    "[1] NASA records | The Apollo 11 mission launched on July 16 and returned on July 24, 1969.\n"
                    "Summary: Apollo 11 launched on July 16 and returned on July 24, 1969.\n"
                    "Missing: None - all claim elements are verified.\n"
                    "Apollo 11 mission dates OR NASA Apollo 11 timeline OR moon landing year confirmation"
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Retrieve fifth-hop passages (final hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [8],
            },
        ],
    }
