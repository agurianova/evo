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
                "aim": "Extract key facts from initial retrieved passages and generate a precise search query for missing evidence.",
                "stage_action": (
                    "Analyze the retrieved passages to identify key facts relevant to the claim and determine what specific information is missing to verify the claim. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine alternative terms if needed). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?\n"
                    "5. What search terms would capture this missing information from multiple angles?\n"
                    "6. How can you structure the query using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Analysis: The claim requires evidence that Neil Armstrong was the first to step on the moon. The passages confirm the mission and crew but do not specify Armstrong as the first to step.\n"
                    "Neil Armstrong first step moon OR first person moon landing"
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
                "aim": "Extract key facts from second-hop retrieved passages and generate a precise search query for remaining missing evidence.",
                "stage_action": (
                    "Analyze the retrieved passages to identify new evidence relevant to the claim and determine what specific information is still missing to verify the claim. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine alternative terms if needed). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence connect to the original claim and previous evidence?\n"
                    "3. What specific information is still missing to verify the claim?\n"
                    "4. What search terms would capture this missing information from multiple angles?\n"
                    "5. How can you structure the query using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous summary: 'Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.'\n"
                    "Passages:\n"
                    "[1] Moon landing | Neil Armstrong was the first human to step onto the lunar surface.\n"
                    "Analysis: The new passage confirms Armstrong was first to step, but missing exact timestamp verification.\n"
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
                "aim": "Extract key facts from third-hop retrieved passages and generate a precise search query for remaining missing evidence.",
                "stage_action": (
                    "Analyze the retrieved passages to identify new evidence relevant to the claim and determine what specific information is still missing to verify the claim. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine alternative terms if needed). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence connect to the original claim and previous evidence?\n"
                    "3. What specific information is still missing to verify the claim?\n"
                    "4. What search terms would capture this missing information from multiple angles?\n"
                    "5. How can you structure the query using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous summary: 'Apollo 11 landed on the moon on July 20, 1969.'\n"
                    "Passages:\n"
                    "[1] Historical events | The Apollo 11 mission concluded in 1969.\n"
                    "Analysis: The passage confirms the mission concluded in 1969, but missing official NASA documentation.\n"
                    "NASA moon landing documentation OR Apollo 11 official records OR NASA 1969 mission report"
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
                "aim": "Extract key facts from fourth-hop retrieved passages and generate a precise search query for final missing evidence.",
                "stage_action": (
                    "Analyze the retrieved passages to identify new evidence relevant to the claim and determine what specific information is still missing to verify the claim. "
                    "Then, generate a single search query string that covers multiple angles of the missing evidence (using OR to combine alternative terms if needed). "
                    "Output ONLY the search query string with no additional text, formatting, or explanations."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence complete the verification picture?\n"
                    "3. What critical information is still missing to fully verify the claim?\n"
                    "4. What are the most precise search terms for the final evidence?\n"
                    "5. How can you structure the query to maximize precision and recall?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous summary: 'Neil Armstrong was the first human to step onto the lunar surface during Apollo 11.'\n"
                    "Passages:\n"
                    "[1] NASA archives | Official records confirm Armstrong stepped onto the moon at 02:56 UTC on July 21, 1969.\n"
                    "Analysis: The passage provides timestamp verification, but missing primary source citation.\n"
                    "NASA primary source Armstrong moon step OR Apollo 11 mission transcript OR moon landing primary documentation"
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
