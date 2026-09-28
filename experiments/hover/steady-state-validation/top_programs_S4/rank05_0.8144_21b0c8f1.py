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
                "title": "Summarize first-hop evidence and identify missing information",
                "step_type": "llm",
                "aim": "Extract key facts from initial retrieved passages and identify missing evidence needed for verification.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. "
                    "Then, list the specific information still missing to fully verify the claim under a 'Missing:' section."
                ),
                "reasoning_questions": (
                    "1. What is the main claim being verified?\n"
                    "2. Which retrieved passages contain facts directly supporting or refuting the claim?\n"
                    "3. What are the key facts from these passages?\n"
                    "4. What specific information is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Passages:\n"
                    "[1] Apollo 11 | Apollo 11 landed on the moon on July 20, 1969.\n"
                    "[2] Crew | The crew included Neil Armstrong and Buzz Aldrin.\n"
                    "Relevant passages: [1] and [2] provide mission details and crew members.\n"
                    "Key facts: Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.\n"
                    "Summary: 'Apollo 11, with crew Neil Armstrong and Buzz Aldrin, landed on the moon on July 20, 1969.'\n"
                    "Missing: Neil Armstrong's role as the first person to step on the moon."
                ),
                "dependencies": [1],
            },
            {
                "number": 3,
                "title": "Generate second-hop query (comprehensive)",
                "step_type": "llm",
                "aim": "Generate a precise and comprehensive search query to retrieve evidence for the missing information.",
                "stage_action": (
                    "Based on the 'Missing:' section from the previous step, create a single search query string "
                    "that covers multiple angles of the missing evidence. Use OR to combine alternative terms if needed "
                    "(e.g., 'term1 OR term2'). Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific information is missing (from the 'Missing:' section)?\n"
                    "2. What are multiple ways to phrase the query to capture different aspects of this missing information?\n"
                    "3. How can you combine these phrases using OR to maximize recall?"
                ),
                "example_reasoning": (
                    "Missing: Neil Armstrong's role as the first person to step on the moon\n"
                    "Possible queries: 'Neil Armstrong first man moon', 'Neil Armstrong first step moon', 'first person moon landing'\n"
                    "Neil Armstrong first man moon OR Neil Armstrong first step moon OR first person moon landing"
                ),
                "dependencies": [2],
            },
            {
                "number": 4,
                "title": "Retrieve second-hop passages (intermediate hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [3],
            },
            {
                "number": 5,
                "title": "Summarize second-hop evidence and identify missing information",
                "step_type": "llm",
                "aim": "Extract key facts from second-hop retrieved passages and identify remaining missing evidence.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. "
                    "Then, list the specific information still missing to fully verify the claim under a 'Missing:' section."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence connect to the original claim and previous evidence?\n"
                    "3. What specific information is still missing to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'Neil Armstrong was the first person on the moon.'\n"
                    "Previous summary: 'Apollo 11 landed on the moon on July 20, 1969 with crew Neil Armstrong and Buzz Aldrin.'\n"
                    "Passages:\n"
                    "[1] Moon landing | Neil Armstrong was the first human to step onto the lunar surface.\n"
                    "New evidence: Neil Armstrong was the first to step on the moon.\n"
                    "Summary: 'Neil Armstrong was the first human to step onto the lunar surface during Apollo 11.'\n"
                    "Missing: None - all claim elements are now verified."
                ),
                "dependencies": [4],
            },
            {
                "number": 6,
                "title": "Generate third-hop query (comprehensive)",
                "step_type": "llm",
                "aim": "Generate a precise search query for any remaining missing evidence.",
                "stage_action": (
                    "Based on the 'Missing:' section from the previous step, create a single search query string "
                    "that covers multiple angles of the missing evidence. Use OR to combine alternative terms if needed. "
                    "Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": (
                    "1. What specific information is still missing (from the 'Missing:' section)?\n"
                    "2. What search terms would capture this missing information from multiple angles?\n"
                    "3. How can you structure the query for maximum recall?"
                ),
                "example_reasoning": (
                    "Missing: Verification of the exact time Armstrong stepped on the moon\n"
                    "Neil Armstrong step time moon OR moon landing timestamp OR first step moon time"
                ),
                "dependencies": [5],
            },
            {
                "number": 7,
                "title": "Retrieve third-hop passages (intermediate hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [6],
            },
            {
                "number": 8,
                "title": "Summarize third-hop evidence and identify missing information",
                "step_type": "llm",
                "aim": "Extract key facts from third-hop retrieved passages and identify any final missing evidence.",
                "stage_action": (
                    "Read the retrieved passages and create a concise summary of relevant facts. "
                    "Then, list the specific information still missing to fully verify the claim under a 'Missing:' section."
                ),
                "reasoning_questions": (
                    "1. What new evidence was found in these passages?\n"
                    "2. How does this evidence complete the verification picture?\n"
                    "3. Is there any remaining information needed to verify the claim?"
                ),
                "example_reasoning": (
                    "Claim: 'The moon landing occurred in 1969.'\n"
                    "Previous summary: 'Apollo 11 landed on the moon on July 20, 1969.'\n"
                    "Passages:\n"
                    "[1] Historical events | The Apollo 11 mission concluded in 1969.\n"
                    "New evidence: The mission concluded in 1969, confirming the year.\n"
                    "Summary: 'Apollo 11 landed on the moon on July 20, 1969 and concluded in 1969.'\n"
                    "Missing: None - the claim about the year 1969 is verified."
                ),
                "dependencies": [7],
            },
            {
                "number": 9,
                "title": "Generate fourth-hop query (comprehensive)",
                "step_type": "llm",
                "aim": "Generate a final search query for any critical missing evidence.",
                "stage_action": (
                    "Based on the 'Missing:' section from the previous step, create a single search query string "
                    "that covers multiple angles of the missing evidence. Use OR to combine alternative terms if needed. "
                    "Output ONLY the search query string with no additional text."
                ),
                "reasoning_questions": (
                    "1. What critical information is still missing (from the 'Missing:' section)?\n"
                    "2. What are the most precise search terms to retrieve this final evidence?\n"
                    "3. How can you structure the query to maximize precision and recall?"
                ),
                "example_reasoning": (
                    "Missing: Official NASA confirmation of Armstrong's first step\n"
                    "NASA Armstrong first step verification OR NASA moon landing confirmation OR official moon landing records"
                ),
                "dependencies": [8],
            },
            {
                "number": 10,
                "title": "Retrieve fourth-hop passages (final hop)",
                "step_type": "tool",
                "step_config": {
                    "tool_name": "retrieve_deep",
                    "input_mapping": {"query": "$history[-1]"},
                },
                "dependencies": [9],
            },
        ],
    }
